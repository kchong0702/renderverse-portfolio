import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import DatabaseSettings
from src.infrastructure.persistence import (
    PostgresTaskOwners,
    create_engine,
    metadata,
)
from src.infrastructure.persistence.task_owners import task_owners

DATABASE_URL = os.environ.get("EZCAREER_HARNESS_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not DATABASE_URL, reason="EZCAREER_HARNESS_TEST_DATABASE_URL is not set"
    ),
]


@pytest.fixture
async def engines() -> AsyncIterator[list[AsyncEngine]]:
    """Two engines on a fresh schema holding task_owners, one per process"""
    settings = DatabaseSettings(
        url=SecretStr(DATABASE_URL), schema_name=f"owners_{uuid4().hex[:8]}"
    )
    engines = [create_engine(settings), create_engine(settings)]
    async with engines[0].begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{settings.schema_name}"'))
        await connection.run_sync(metadata.create_all)
    yield engines
    async with engines[0].begin() as connection:
        await connection.execute(text(f'DROP SCHEMA "{settings.schema_name}" CASCADE'))
    for engine in engines:
        await engine.dispose()


async def _age(engine: AsyncEngine, seconds: int) -> None:
    """Backdates every heartbeat by seconds"""
    async with engine.begin() as connection:
        await connection.execute(
            update(task_owners).values(
                heartbeat_at=task_owners.c.heartbeat_at
                - text(f"interval '{seconds} seconds'")
            )
        )


async def test_a_dead_owners_tasks_are_taken_over_and_a_live_owners_are_not(engines):
    dead, live, sweeper = (
        PostgresTaskOwners(engines[0]),
        PostgresTaskOwners(engines[0]),
        PostgresTaskOwners(engines[1]),
    )
    await dead.claim("task-1")
    await _age(engines[0], 40)
    await live.claim("task-2")

    taken = await sweeper.take_stale(30)

    assert taken == ["task-1"]
    assert await sweeper.beat() == {"task-1"}
    assert await dead.beat() == set()
    assert await live.beat() == {"task-2"}


async def test_two_sweepers_racing_take_each_dead_task_once(engines):
    dead = PostgresTaskOwners(engines[0])
    for number in range(50):
        await dead.claim(f"task-{number}")
    await _age(engines[0], 40)
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    taken = await asyncio.gather(first.take_stale(30), second.take_stale(30))

    assert sorted(taken[0] + taken[1]) == sorted(f"task-{n}" for n in range(50))
    assert set(taken[0]).isdisjoint(taken[1])


async def test_a_task_with_no_owner_is_taken_once_and_a_live_owners_never(engines):
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    won = await asyncio.gather(
        first.take_unowned("task-1", 30), second.take_unowned("task-1", 30)
    )

    assert sorted(won) == [False, True]
    assert not await first.take_unowned("task-1", 30)
    assert not await second.take_unowned("task-1", 30)


async def test_a_released_task_is_taken_at_once_and_drop_spares_other_owners(engines):
    leaving, staying = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])
    await leaving.claim("task-1")
    await leaving.release()

    assert await staying.take_stale(30) == ["task-1"]
    await leaving.drop("task-1")
    assert await staying.beat() == {"task-1"}
    await staying.drop("task-1")
    assert await staying.beat() == set()


async def test_a_thread_is_held_by_one_run_at_a_time_across_processes(engines):
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    async with first.thread("thread-1", 1) as held:
        async with second.thread("thread-1", 0.3) as waited:
            pass
        async with second.thread("thread-2", 0.3) as other:
            pass
    async with second.thread("thread-1", 0.3) as later:
        pass

    assert held and not waited and other and later


async def test_a_run_waiting_for_its_thread_gets_it_once_the_holder_lets_go(engines):
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])
    holding = asyncio.Event()

    async def hold_briefly() -> None:
        async with first.thread("thread-1", 1):
            holding.set()
            await asyncio.sleep(0.5)

    holder = asyncio.create_task(hold_briefly())
    await holding.wait()
    async with second.thread("thread-1", 5) as held:
        let_go = holder.done()

    assert held and let_go


async def test_a_thread_whose_holder_lost_its_connection_is_free(engines):
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    async with first.thread("thread-1", 1):
        async with engines[1].begin() as connection:
            await connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_locks"
                    " WHERE locktype = 'advisory' AND granted"
                    " AND objid = hashtext('ezcareer thread thread-1')::oid"
                )
            )
        async with second.thread("thread-1", 2) as held:
            pass

    assert held
