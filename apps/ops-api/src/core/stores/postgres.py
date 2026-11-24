import asyncio
import secrets
import socket
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import DatabaseSettings, EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.stores.enums import AgentRunStatus
from src.core.stores.errors import RunLost
from src.core.stores.models import AgentEvent, AgentRun
from src.core.stores.protocol import RunRecord
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
        """The replay window, when a run's owner counts as dead and how often to poll"""

        self._owner = f"{socket.gethostname()}:{uuid4().hex[:8]}"
        """This process's owner id, new on each start so a restart never looks alive"""

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

    def _dropped(self, connection: asyncpg.Connection) -> None:
        """Forget the listening connection once it closes, so the next read reopens it"""
        self._listener = None

    async def _listen(self) -> None:
        """Open this process's listening connection once"""
        async with self._opening:
            if self._listener is None:
                listener = await asyncpg.connect(
                    self._dsn.render_as_string(hide_password=False)
                )
                await listener.add_listener(_CHANNEL, self._notified)
                listener.add_termination_listener(self._dropped)
                self._listener = listener

    async def create(self, user_id: UUID, thread_id: str, agent: str) -> str:
        """Open a running run of the user's agent on thread_id, owned by this process,
        one create per thread at a time; Conflict while thread_id's last run is running"""
        async with self._factory() as session, session.begin():
            await session.execute(
                select(func.pg_advisory_xact_lock(func.hashtext(thread_id)))
            )
            running = await session.scalar(
                select(AgentRun.id).where(
                    AgentRun.thread_id == thread_id,
                    AgentRun.status == AgentRunStatus.RUNNING,
                )
            )
            if running:
                raise Conflict("Wait for the current reply to finish")
            await session.execute(
                delete(AgentRun).where(AgentRun.thread_id == thread_id)
            )
            run = AgentRun(
                id=secrets.token_hex(8),
                user_id=user_id,
                thread_id=thread_id,
                agent=agent,
                status=AgentRunStatus.RUNNING,
                owner=self._owner,
                heartbeat_at=func.now(),
            )
            session.add(run)
        return run.id

    async def append(self, run_id: str, seq: int, data: dict[str, Any]) -> None:
        """Keep the run's event and notify every process reading it; RunLost once
        another process took the run over"""
        async with self._factory() as session, session.begin():
            user_id = await session.scalar(
                select(AgentRun.user_id)
                .where(AgentRun.id == run_id, AgentRun.owner == self._owner)
                .with_for_update()
            )
            if user_id is None:
                raise RunLost(run_id)
            await session.execute(
                insert(AgentEvent).values(
                    user_id=user_id, run_id=run_id, seq=seq, data=data
                )
            )
            await session.execute(select(func.pg_notify(_CHANNEL, run_id)))

    async def set_task(self, run_id: str, task_id: str) -> None:
        """Keep the A2A task the run follows; RunLost once another process took the
        run over"""
        async with self._factory() as session, session.begin():
            if (
                await session.scalar(
                    update(AgentRun)
                    .where(AgentRun.id == run_id, AgentRun.owner == self._owner)
                    .values(task_id=task_id)
                    .returning(AgentRun.id)
                )
                is None
            ):
                raise RunLost(run_id)

    async def finish(
        self, run_id: str, status: AgentRunStatus, task_id: str | None
    ) -> None:
        """Mark the run ended with status and the A2A task it ran, and notify every
        process reading it; RunLost once another process took the run over"""
        async with self._factory() as session, session.begin():
            if (
                await session.scalar(
                    update(AgentRun)
                    .where(AgentRun.id == run_id, AgentRun.owner == self._owner)
                    .values(status=status, task_id=task_id, finished_at=utcnow())
                    .returning(AgentRun.id)
                )
                is None
            ):
                raise RunLost(run_id)
            await session.execute(select(func.pg_notify(_CHANNEL, run_id)))

    async def latest(self, thread_id: str) -> tuple[str, int]:
        """thread_id's run a client may still read and how many events it has; NotFound
        once it ended over replay_ttl_seconds ago"""
        replay_after = utcnow() - timedelta(seconds=self._settings.replay_ttl_seconds)
        async with self._factory() as session:
            run = await session.scalar(
                select(AgentRun).where(AgentRun.thread_id == thread_id)
            )
            if run is None or (
                run.finished_at is not None and run.finished_at < replay_after
            ):
                raise NotFound("There is no reply to resume")
            count = (
                await session.execute(
                    select(func.count()).where(AgentEvent.run_id == run.id)
                )
            ).scalar_one()
        return run.id, count

    async def paused(self, thread_id: str) -> tuple[str, str] | None:
        """The task thread_id's last run paused on and the status of its last event;
        None unless that run ended asking the user"""
        async with self._factory() as session:
            run = await session.scalar(
                select(AgentRun).where(AgentRun.thread_id == thread_id)
            )
            if (
                run is None
                or run.status != AgentRunStatus.INPUT_REQUIRED
                or run.task_id is None
            ):
                return None
            last = await session.scalar(
                select(AgentEvent.data)
                .where(AgentEvent.run_id == run.id)
                .order_by(AgentEvent.seq.desc())
                .limit(1)
            )
        return run.task_id, last["status"] if last else ""

    async def abandoned(
        self, thread_id: str
    ) -> tuple[str, str | None, datetime] | None:
        """The id, A2A task if known and start of thread_id's last run when ops-api gave
        up following it; None otherwise"""
        async with self._factory() as session:
            run = await session.scalar(
                select(AgentRun).where(
                    AgentRun.thread_id == thread_id,
                    AgentRun.status == AgentRunStatus.ABANDONED,
                )
            )
        return (run.id, run.task_id, run.created_at) if run else None

    async def read(self, run_id: str, after: int) -> AsyncIterator[dict[str, Any]]:
        """The run's events after the first `after`, then each new one until it ends"""
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
            if run is None or run.status != AgentRunStatus.RUNNING:
                self._changed.pop(run_id, None)
                return
            with suppress(TimeoutError):
                await asyncio.wait_for(
                    changed.wait(), timeout=self._settings.run_poll_seconds
                )

    async def heartbeat(self) -> set[str]:
        """Mark this process alive on every running run it owns and return their ids"""
        async with self._factory() as session, session.begin():
            return set(
                (
                    await session.scalars(
                        update(AgentRun)
                        .where(
                            AgentRun.owner == self._owner,
                            AgentRun.status == AgentRunStatus.RUNNING,
                        )
                        .values(heartbeat_at=func.now())
                        .returning(AgentRun.id)
                    )
                ).all()
            )

    async def sweep(self) -> list[RunRecord]:
        """Take over every running run whose owner missed its heartbeats past
        dead_after_seconds, with how many events each kept"""
        async with self._factory() as session, session.begin():
            taken = (
                await session.scalars(
                    update(AgentRun)
                    .where(
                        AgentRun.status == AgentRunStatus.RUNNING,
                        AgentRun.owner.is_distinct_from(self._owner),
                        AgentRun.heartbeat_at
                        < func.now()
                        - timedelta(seconds=self._settings.dead_after_seconds),
                    )
                    .values(owner=self._owner, heartbeat_at=func.now())
                    .returning(AgentRun.id)
                )
            ).all()
        if not taken:
            return []
        events = (
            select(func.count())
            .where(AgentEvent.run_id == AgentRun.id)
            .correlate(AgentRun)
            .scalar_subquery()
        )
        async with self._factory() as session:
            rows = (
                await session.execute(
                    select(AgentRun, events).where(AgentRun.id.in_(taken))
                )
            ).all()
        return [
            RunRecord(
                id=run.id,
                user_id=run.user_id,
                thread_id=run.thread_id,
                agent=run.agent,
                task_id=run.task_id,
                started_at=run.created_at,
                events=count,
            )
            for run, count in rows
        ]

    async def release(self) -> None:
        """Date back the heartbeat of this process's running runs, so the next sweep
        anywhere takes them over"""
        async with self._factory() as session, session.begin():
            await session.execute(
                update(AgentRun)
                .where(
                    AgentRun.owner == self._owner,
                    AgentRun.status == AgentRunStatus.RUNNING,
                )
                .values(heartbeat_at=func.now() - timedelta(hours=1))
            )

    async def aclose(self) -> None:
        """Close this process's listening connection"""
        if self._listener is not None:
            await self._listener.close()


__all__ = ["PostgresRunStore"]
