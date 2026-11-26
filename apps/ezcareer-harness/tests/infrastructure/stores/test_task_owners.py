import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import DatabaseSettings
from src.infrastructure.stores import (
    PostgresTaskOwners,
    create_engine,
    metadata,
)
from src.infrastructure.stores.task_owners import task_owners

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

    taken = await sweeper.take_over_dead(30)

    assert taken == ["task-1"]
    assert await sweeper.heartbeat() == {"task-1"}
    assert await dead.heartbeat() == set()
    assert await live.heartbeat() == {"task-2"}


async def test_two_sweepers_racing_take_each_dead_task_once(engines):
    dead = PostgresTaskOwners(engines[0])
    for number in range(50):
        await dead.claim(f"task-{number}")
    await _age(engines[0], 40)
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    taken = await asyncio.gather(first.take_over_dead(30), second.take_over_dead(30))

    assert sorted(taken[0] + taken[1]) == sorted(f"task-{n}" for n in range(50))
    assert set(taken[0]).isdisjoint(taken[1])


async def test_a_task_with_no_owner_is_taken_once_and_a_live_owners_never(engines):
    first, second = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])

    won = await asyncio.gather(
        first.take_over_unowned("task-1", 30), second.take_over_unowned("task-1", 30)
    )

    assert sorted(won) == [False, True]
    assert not await first.take_over_unowned("task-1", 30)
    assert not await second.take_over_unowned("task-1", 30)


async def test_a_handed_over_task_is_taken_at_once_and_unclaim_spares_other_owners(
    engines,
):
    leaving, staying = PostgresTaskOwners(engines[0]), PostgresTaskOwners(engines[1])
    await leaving.claim("task-1")
    await leaving.hand_over_all()

    assert await staying.take_over_dead(30) == ["task-1"]
    await leaving.unclaim("task-1")
    assert await staying.heartbeat() == {"task-1"}
    await staying.unclaim("task-1")
    assert await staying.heartbeat() == set()
