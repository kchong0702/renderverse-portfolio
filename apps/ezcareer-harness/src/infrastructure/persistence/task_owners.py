import asyncio
import socket
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import override
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    MetaData,
    Table,
    Text,
    delete,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

metadata = MetaData()
"""The harness's own tables, which its Alembic migrations create"""

task_owners = Table(
    "task_owners",
    metadata,
    Column("task_id", Text, primary_key=True),
    Column("owner", Text, nullable=False),
    Column(
        "heartbeat_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Index("ix_task_owners_heartbeat", "heartbeat_at"),
)
"""Which process runs each running A2A task, and when it last said it is alive"""


class TaskOwners(ABC):
    def __init__(self) -> None:
        """Names this process start, so a restarted pod never passes for the old one"""
        self.me = f"{socket.gethostname()}:{uuid4().hex[:8]}"
        """This process's name in the owner column, its host and a random suffix"""

    @abstractmethod
    async def claim(self, task_id: str) -> None:
        """Makes this process the task's owner"""

    @abstractmethod
    async def drop(self, task_id: str) -> None:
        """Deletes the task's row while this process owns it"""

    @abstractmethod
    async def owns(self, task_id: str) -> bool:
        """Whether this process still owns the task"""

    @abstractmethod
    async def beat(self) -> set[str]:
        """Refreshes the heartbeat of every task this process owns; returns their
        ids"""

    @abstractmethod
    async def take_stale(self, dead_after_seconds: float) -> list[str]:
        """Takes over each task whose other owner has not beaten for
        dead_after_seconds; returns their ids"""

    @abstractmethod
    async def take_unowned(self, task_id: str, dead_after_seconds: float) -> bool:
        """Owns the task unless a live owner holds it; whether it did"""

    @abstractmethod
    async def release(self) -> None:
        """Marks this process's tasks dead so the next sweep elsewhere takes them"""

    @abstractmethod
    def thread(
        self, thread_id: str, wait_seconds: float
    ) -> AbstractAsyncContextManager[bool]:
        """Holds exclusive use of the thread while open, waiting up to wait_seconds
        for any other holder to let go; whether it got it"""


class PostgresTaskOwners(TaskOwners):
    def __init__(self, engine: AsyncEngine) -> None:
        """Task owners in the task_owners table, by the database's clock"""
        super().__init__()
        self.engine = engine
        """The engine on the harness's schema that holds task_owners"""

        self.locks = create_async_engine(
            engine.url,
            poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
            connect_args={
                "options": "-c tcp_keepalives_idle=10"
                " -c tcp_keepalives_interval=5 -c tcp_keepalives_count=3"
            },
        )
        """Unpooled connections that each hold one thread's lock, which Postgres lets
        go of when the connection closes or, by keepalive, when its process is gone"""

    @override
    async def claim(self, task_id: str) -> None:
        """Upserts the task's row with this process as owner"""
        async with self.engine.begin() as connection:
            await connection.execute(
                insert(task_owners)
                .values(task_id=task_id, owner=self.me)
                .on_conflict_do_update(
                    index_elements=[task_owners.c.task_id],
                    set_={"owner": self.me, "heartbeat_at": func.now()},
                )
            )

    @override
    async def drop(self, task_id: str) -> None:
        """Deletes the task's row where this process is the owner"""
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(task_owners).where(
                    task_owners.c.task_id == task_id, task_owners.c.owner == self.me
                )
            )

    @override
    async def owns(self, task_id: str) -> bool:
        """Whether the task's row names this process"""
        async with self.engine.connect() as connection:
            owner = await connection.scalar(
                select(task_owners.c.owner).where(task_owners.c.task_id == task_id)
            )
            return owner == self.me

    @override
    async def beat(self) -> set[str]:
        """Sets heartbeat_at to now on every row this process owns, in one statement"""
        async with self.engine.begin() as connection:
            rows = await connection.execute(
                update(task_owners)
                .where(task_owners.c.owner == self.me)
                .values(heartbeat_at=func.now())
                .returning(task_owners.c.task_id)
            )
            return set(rows.scalars())

    @override
    async def take_stale(self, dead_after_seconds: float) -> list[str]:
        """Moves every row whose heartbeat is too old to this process, in one
        statement, so only one of two racing sweepers wins each row"""
        async with self.engine.begin() as connection:
            rows = await connection.execute(
                update(task_owners)
                .where(
                    task_owners.c.owner != self.me,
                    task_owners.c.heartbeat_at
                    < func.now() - timedelta(seconds=dead_after_seconds),
                )
                .values(owner=self.me, heartbeat_at=func.now())
                .returning(task_owners.c.task_id)
            )
            return list(rows.scalars())

    @override
    async def take_unowned(self, task_id: str, dead_after_seconds: float) -> bool:
        """Inserts the task's row, or takes it over when its heartbeat is too old"""
        async with self.engine.begin() as connection:
            rows = await connection.execute(
                insert(task_owners)
                .values(task_id=task_id, owner=self.me)
                .on_conflict_do_update(
                    index_elements=[task_owners.c.task_id],
                    set_={"owner": self.me, "heartbeat_at": func.now()},
                    where=task_owners.c.heartbeat_at
                    < func.now() - timedelta(seconds=dead_after_seconds),
                )
                .returning(task_owners.c.task_id)
            )
            return rows.first() is not None

    @override
    async def release(self) -> None:
        """Backdates this process's heartbeats by an hour"""
        async with self.engine.begin() as connection:
            await connection.execute(
                update(task_owners)
                .where(task_owners.c.owner == self.me)
                .values(heartbeat_at=func.now() - timedelta(hours=1))
            )

    @override
    @asynccontextmanager
    async def thread(self, thread_id: str, wait_seconds: float) -> AsyncIterator[bool]:
        """Holds a session advisory lock on the thread on a connection of its own,
        trying again until wait_seconds pass"""
        async with self.locks.connect() as connection:
            deadline = time.monotonic() + wait_seconds
            while (
                not (
                    held := bool(
                        await connection.scalar(
                            text(
                                "SELECT pg_try_advisory_lock("
                                "hashtext('ezcareer thread ' || :thread_id))"
                            ),
                            {"thread_id": thread_id},
                        )
                    )
                )
                and time.monotonic() < deadline
            ):
                await asyncio.sleep(0.1)
            yield held


class MemoryTaskOwners(TaskOwners):
    def __init__(
        self,
        rows: dict[str, tuple[str, datetime]] | None = None,
        threads: set[str] | None = None,
    ) -> None:
        """Task owners in a dict of owner and heartbeat by task id, and held threads
        in a set, which tests share between app instances"""
        super().__init__()
        self.rows = {} if rows is None else rows
        """Each task's owner and last heartbeat, by task id"""

        self.threads = set() if threads is None else threads
        """The threads a run holds"""

    @override
    async def claim(self, task_id: str) -> None:
        """Sets the task's row to this process, beating now"""
        self.rows[task_id] = (self.me, datetime.now(UTC))

    @override
    async def drop(self, task_id: str) -> None:
        """Deletes the task's row where this process is the owner"""
        if await self.owns(task_id):
            del self.rows[task_id]

    @override
    async def owns(self, task_id: str) -> bool:
        """Whether the task's row names this process"""
        return task_id in self.rows and self.rows[task_id][0] == self.me

    @override
    async def beat(self) -> set[str]:
        """Sets the heartbeat of every row this process owns to now"""
        mine = {
            task_id for task_id, (owner, _) in self.rows.items() if owner == self.me
        }
        for task_id in mine:
            self.rows[task_id] = (self.me, datetime.now(UTC))
        return mine

    @override
    async def take_stale(self, dead_after_seconds: float) -> list[str]:
        """Moves every row whose heartbeat is too old to this process"""
        cutoff = datetime.now(UTC) - timedelta(seconds=dead_after_seconds)
        stale = [
            task_id
            for task_id, (owner, heartbeat_at) in self.rows.items()
            if owner != self.me and heartbeat_at < cutoff
        ]
        for task_id in stale:
            self.rows[task_id] = (self.me, datetime.now(UTC))
        return stale

    @override
    async def take_unowned(self, task_id: str, dead_after_seconds: float) -> bool:
        """Sets the task's row to this process unless a live owner holds it"""
        cutoff = datetime.now(UTC) - timedelta(seconds=dead_after_seconds)
        if task_id in self.rows and self.rows[task_id][1] >= cutoff:
            return False
        self.rows[task_id] = (self.me, datetime.now(UTC))
        return True

    @override
    async def release(self) -> None:
        """Backdates this process's heartbeats by an hour"""
        for task_id, (owner, _) in [*self.rows.items()]:
            if owner == self.me:
                self.rows[task_id] = (owner, datetime.now(UTC) - timedelta(hours=1))

    @override
    @asynccontextmanager
    async def thread(self, thread_id: str, wait_seconds: float) -> AsyncIterator[bool]:
        """Adds the thread to the held set once no run holds it, trying again until
        wait_seconds pass, and removes it on close"""
        deadline = time.monotonic() + wait_seconds
        while thread_id in self.threads and time.monotonic() < deadline:
            await asyncio.sleep(0.1)
        held = thread_id not in self.threads
        if held:
            self.threads.add(thread_id)
        try:
            yield held
        finally:
            if held:
                self.threads.discard(thread_id)
