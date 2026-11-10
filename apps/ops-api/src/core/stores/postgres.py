import asyncio
import secrets
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
from fastapi.sse import ServerSentEvent
from sqlalchemy import delete, func, insert, literal, select, text, update
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
        """The retry hint, the replay window and how long a silent run stays alive"""

        self._listener: asyncpg.Connection | None = None
        """This process's one connection listening on the channel, opened on first read"""

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
        if self._listener is None:
            self._listener = await asyncpg.connect(
                self._dsn.render_as_string(hide_password=False)
            )
            await self._listener.add_listener(_CHANNEL, self._notified)

    def _alive_since(self) -> datetime:
        """The oldest last activity of a run still taken to be running"""
        return utcnow() - timedelta(seconds=self._settings.run_timeout_seconds)

    async def start(self, user_id: UUID, key: str) -> str:
        """Open a new run of the user's for key and return its id; Conflict while key's
        last run is still going and was active within run_timeout_seconds"""
        async with self._factory() as session, session.begin():
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
            await session.execute(
                text("SELECT pg_notify(:channel, :run_id)"),
                {"channel": _CHANNEL, "run_id": run_id},
            )

    async def finish(self, run_id: str) -> None:
        """Mark the run ended and notify every process reading it"""
        async with self._factory() as session, session.begin():
            await session.execute(
                update(AgentRun)
                .where(AgentRun.id == run_id)
                .values(finished_at=utcnow())
            )
            await session.execute(
                text("SELECT pg_notify(:channel, :run_id)"),
                {"channel": _CHANNEL, "run_id": run_id},
            )

    async def resume(self, key: str, last_event_id: str | None) -> tuple[str, int]:
        """Key's run a client may resume and how many of its events it has; NotFound
        once it ended over replay_ttl_seconds ago, went silent past
        run_timeout_seconds, or for another run's event id"""
        async with self._factory() as session:
            run = await session.scalar(select(AgentRun).where(AgentRun.key == key))
            count = (
                await session.scalar(
                    select(func.count()).where(AgentEvent.run_id == run.id)
                )
                if run
                else 0
            )
        replay_after = utcnow() - timedelta(seconds=self._settings.replay_ttl_seconds)
        if (
            run is None
            or (run.finished_at is not None and run.finished_at < replay_after)
            or (run.finished_at is None and run.active_at <= self._alive_since())
        ):
            raise NotFound("There is no reply to resume")
        if not last_event_id:
            return run.id, 0
        run_id, _, seq = last_event_id.partition(":")
        if run_id != run.id or not seq.isdigit():
            raise NotFound("There is no reply to resume")
        return run.id, min(int(seq), count or 0)

    async def read(self, run_id: str, after: int) -> AsyncIterator[ServerSentEvent]:
        """The run's events after the first `after`, then each new one until it ends
        or goes silent past run_timeout_seconds"""
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
                yield ServerSentEvent(
                    raw_data=event.data,
                    id=f"{run_id}:{event.seq}",
                    retry=self._settings.stream_retry_ms if event.seq == 1 else None,
                )
            if (
                run is None
                or run.finished_at is not None
                or run.active_at <= self._alive_since()
            ):
                return
            try:
                await asyncio.wait_for(changed.wait(), timeout=5)
            except TimeoutError:
                pass

    async def aclose(self) -> None:
        """Close this process's listening connection"""
        if self._listener is not None:
            await self._listener.close()
