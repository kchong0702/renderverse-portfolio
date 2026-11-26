import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


class ThreadLock(ABC):
    def __init__(self, wait_seconds: float) -> None:
        """Lets one run at a time use each LangGraph thread"""
        self.wait_seconds = wait_seconds
        """How long hold waits for an earlier run on the thread to stop"""

    @abstractmethod
    def hold(
        self, thread_id: str, wait: bool = True
    ) -> AbstractAsyncContextManager[bool]:
        """Holds exclusive use of the thread while open, waiting up to wait_seconds
        for any other holder to let go unless told not to; whether it got it"""


class PostgresThreadLock(ThreadLock):
    def __init__(self, engine: AsyncEngine, wait_seconds: float) -> None:
        """Thread locks as Postgres session advisory locks, so they hold across
        replicas"""
        super().__init__(wait_seconds)
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
    @asynccontextmanager
    async def hold(self, thread_id: str, wait: bool = True) -> AsyncIterator[bool]:
        """Holds a session advisory lock on the thread on a connection of its own,
        trying again until wait_seconds pass"""
        async with self.locks.connect() as connection:
            deadline = time.monotonic() + (self.wait_seconds if wait else 0)
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


class MemoryThreadLock(ThreadLock):
    def __init__(self, wait_seconds: float, threads: set[str] | None = None) -> None:
        """Thread locks as a set of held threads, which tests share between app
        instances"""
        super().__init__(wait_seconds)
        self.threads = set() if threads is None else threads
        """The threads a run holds"""

    @override
    @asynccontextmanager
    async def hold(self, thread_id: str, wait: bool = True) -> AsyncIterator[bool]:
        """Adds the thread to the held set once no run holds it, trying again until
        wait_seconds pass, and removes it on close"""
        deadline = time.monotonic() + (self.wait_seconds if wait else 0)
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
