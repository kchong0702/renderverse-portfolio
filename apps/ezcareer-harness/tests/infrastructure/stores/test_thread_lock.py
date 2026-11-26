import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import DatabaseSettings
from src.infrastructure.stores import PostgresThreadLock, create_engine

DATABASE_URL = os.environ.get("EZCAREER_HARNESS_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not DATABASE_URL, reason="EZCAREER_HARNESS_TEST_DATABASE_URL is not set"
    ),
]


@pytest.fixture
async def engines() -> AsyncIterator[list[AsyncEngine]]:
    """Two engines on a fresh schema, one per process"""
    settings = DatabaseSettings(
        url=SecretStr(DATABASE_URL), schema_name=f"locks_{uuid4().hex[:8]}"
    )
    engines = [create_engine(settings), create_engine(settings)]
    async with engines[0].begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{settings.schema_name}"'))
    yield engines
    async with engines[0].begin() as connection:
        await connection.execute(text(f'DROP SCHEMA "{settings.schema_name}" CASCADE'))
    for engine in engines:
        await engine.dispose()


async def test_a_thread_is_held_by_one_run_at_a_time_across_processes(engines):
    first = PostgresThreadLock(engines[0], 1)
    second = PostgresThreadLock(engines[1], 0.3)

    async with first.hold("thread-1") as held:
        async with second.hold("thread-1") as waited:
            pass
        async with second.hold("thread-2") as other:
            pass
    async with second.hold("thread-1") as later:
        pass

    assert held and not waited and other and later


async def test_a_thread_that_is_held_is_refused_at_once_without_waiting(engines):
    first = PostgresThreadLock(engines[0], 1)
    second = PostgresThreadLock(engines[1], 60)

    async with first.hold("thread-1"), second.hold("thread-1", wait=False) as held:
        pass

    assert not held


async def test_a_run_waiting_for_its_thread_gets_it_once_the_holder_lets_go(engines):
    first = PostgresThreadLock(engines[0], 1)
    second = PostgresThreadLock(engines[1], 5)
    holding = asyncio.Event()

    async def hold_briefly() -> None:
        async with first.hold("thread-1"):
            holding.set()
            await asyncio.sleep(0.5)

    holder = asyncio.create_task(hold_briefly())
    await holding.wait()
    async with second.hold("thread-1") as held:
        let_go = holder.done()

    assert held and let_go


async def test_a_thread_whose_holder_lost_its_connection_is_free(engines):
    first = PostgresThreadLock(engines[0], 1)
    second = PostgresThreadLock(engines[1], 2)

    async with first.hold("thread-1"):
        async with engines[1].begin() as connection:
            await connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_locks"
                    " WHERE locktype = 'advisory' AND granted"
                    " AND objid = hashtext('ezcareer thread thread-1')::oid"
                )
            )
        async with second.hold("thread-1") as held:
            pass

    assert held
