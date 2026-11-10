import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
from sqlalchemy import delete, func, insert, literal, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import DatabaseSettings, EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.stores.models import AgentEvent, AgentRun
from src.db.base import utcnow

_CHANNEL = "agent_runs"


class PostgresRunStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        database: DatabaseSettings,
        settings: EzcareerSettings,
    ):
        """Keep runs in Postgres so every ops-api process can replay and follow them;
        LISTEN/NOTIFY wakes a reader in any process when its run changes"""
        self._factory = session_factory
        """Sessions for reading and writing runs"""

        self._dsn = make_url(database.url.get_secret_value()).set(
            drivername="postgresql"
        )
        """Where the listening connection connects"""

        self._settings = settings
        """The replay window, how long a silent run stays alive and how often to poll"""

        self._listener: asyncpg.Connection | None = None
        """This process's one connection listening on the channel, opened on first read"""

        self._opening = asyncio.Lock()
        """Held while the listening connection opens, so only one ever does"""

        self._changed: dict[str, asyncio.Event] = {}
        """The event each run's readers in this process wait on, by run id"""

    def _notified(
        self, connection: asyncpg.Connection, pid: int, channel: str, run_id: str
    ) -> None:
        """Wake this process's readers of the run a notification names"""
        if changed := self._changed.pop(run_id, None):
            changed.set()

    async def _listen(self) -> None:
        """Open this process's listening connection once"""
        async with self._opening:
            if self._listener is None:
                listener = await asyncpg.connect(
                    self._dsn.render_as_string(hide_password=False)
                )
                await listener.add_listener(_CHANNEL, self._notified)
                self._listener = listener

    def _alive_since(self) -> datetime:
        """The oldest last activity of a run still taken to be running"""
        return utcnow() - timedelta(seconds=self._settings.run_timeout_seconds)

    async def create(self, user_id: UUID, key: str) -> str:
        """Open a new run of the user's for key and return its id, one create per key at
        a time; Conflict while key's last run is still going and recently active"""
        async with self._factory() as session, session.begin():
            await session.execute(
                select(func.pg_advisory_xact_lock(func.hashtext(key)))
            )
            running = await session.scalar(
                select(AgentRun.id).where(
                    AgentRun.key == key,
                    AgentRun.finished_at.is_(None),
                    AgentRun.active_at > self._alive_since(),
                )
            )
            if running:
                raise Conflict("Wait for the current reply to finish")
            await session.execute(delete(AgentRun).where(AgentRun.key == key))
            run = AgentRun(id=secrets.token_hex(8), user_id=user_id, key=key)
            session.add(run)
        return run.id

    async def append(self, run_id: str, seq: int, data: str) -> None:
        """Keep the run's event and notify every process reading it"""
        async with self._factory() as session, session.begin():
            await session.execute(
                insert(AgentEvent).from_select(
                    ["user_id", "run_id", "seq", "data"],
                    select(
                        AgentRun.user_id,
                        literal(run_id),
                        literal(seq),
                        literal(data),
                    ).where(AgentRun.id == run_id),
                )
            )
            await session.execute(
                update(AgentRun).where(AgentRun.id == run_id).values(active_at=utcnow())
            )
            await session.execute(select(func.pg_notify(_CHANNEL, run_id)))

    async def finish(self, run_id: str) -> None:
        """Mark the run ended and notify every process reading it"""
        async with self._factory() as session, session.begin():
            await session.execute(
                update(AgentRun)
                .where(AgentRun.id == run_id)
                .values(finished_at=utcnow())
            )
            await session.execute(select(func.pg_notify(_CHANNEL, run_id)))

    async def latest(self, key: str) -> tuple[str, int]:
        """Key's run a client may still read and how many events it has; NotFound once
        it ended over replay_ttl_seconds ago or went silent past run_timeout_seconds"""
        replay_after = utcnow() - timedelta(seconds=self._settings.replay_ttl_seconds)
        async with self._factory() as session:
            run = await session.scalar(select(AgentRun).where(AgentRun.key == key))
            if (
                run is None
                or (run.finished_at is not None and run.finished_at < replay_after)
                or (run.finished_at is None and run.active_at <= self._alive_since())
            ):
                raise NotFound("There is no reply to resume")
            count = (
                await session.execute(
                    select(func.count()).where(AgentEvent.run_id == run.id)
                )
            ).scalar_one()
        return run.id, count

    async def read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The JSON data of the run's events after the first `after`, then of each new
        one until it ends or goes silent past run_timeout_seconds"""
        await self._listen()
        sent = after
        while True:
            changed = self._changed.setdefault(run_id, asyncio.Event())
            async with self._factory() as session:
                events = (
                    await session.scalars(
                        select(AgentEvent)
                        .where(AgentEvent.run_id == run_id, AgentEvent.seq > sent)
                        .order_by(AgentEvent.seq)
                    )
                ).all()
                run = await session.get(AgentRun, run_id)
            for event in events:
                sent = event.seq
                yield event.data
            if (
                run is None
                or run.finished_at is not None
                or run.active_at <= self._alive_since()
            ):
                self._changed.pop(run_id, None)
                return
            with suppress(TimeoutError):
                await asyncio.wait_for(
                    changed.wait(), timeout=self._settings.run_poll_seconds
                )

    async def aclose(self) -> None:
        """Close this process's listening connection"""
        if self._listener is not None:
            await self._listener.close()


__all__ = ["PostgresRunStore"]
