import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.stores import AgentRunStatus, InMemoryRunStore, RunStore
from tests.core.conftest import needs_postgres, postgres_store

SETTINGS = EzcareerSettings(replay_ttl_seconds=60)


@pytest.fixture(params=["memory", pytest.param("postgres", marks=needs_postgres)])
def backend(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def user_id(request: pytest.FixtureRequest, backend: str) -> UUID:
    return uuid4() if backend == "memory" else request.getfixturevalue("postgres_user")


@pytest.fixture
async def store(
    request: pytest.FixtureRequest, backend: str, user_id: UUID
) -> AsyncIterator[RunStore]:
    if backend == "memory":
        yield InMemoryRunStore(SETTINGS)
        return
    async with aclosing(
        postgres_store(request.getfixturevalue("engine"), SETTINGS)
    ) as runs:
        yield runs


async def _read(store: RunStore, run_id: str, after: int = 0) -> list[dict[str, Any]]:
    return [data async for data in store.read(run_id, after)]


async def test_a_run_is_read_back_in_order_then_ends(store: RunStore, user_id: UUID):
    run_id = await store.create(user_id, "chat-1", "agent")
    await store.append(run_id, 1, {"status": "started"})
    await store.append(run_id, 2, {"status": "completed"})
    await store.finish(run_id, AgentRunStatus.COMPLETED, None)

    assert await _read(store, run_id) == [
        {"status": "started"},
        {"status": "completed"},
    ]


async def test_a_thread_takes_one_run_at_a_time(store: RunStore, user_id: UUID):
    first = await store.create(user_id, "chat-1", "agent")

    with pytest.raises(Conflict):
        await store.create(user_id, "chat-1", "agent")
    await store.finish(first, AgentRunStatus.COMPLETED, None)
    second = await store.create(user_id, "chat-1", "agent")

    assert second != first
    assert await store.latest("chat-1") == (second, 0)


async def test_a_reader_follows_events_written_after_it_started(
    store: RunStore, user_id: UUID
):
    run_id = await store.create(user_id, "chat-1", "agent")
    reading = asyncio.create_task(_read(store, run_id))
    await asyncio.sleep(0.2)

    await store.append(run_id, 1, {"n": 1})
    await store.finish(run_id, AgentRunStatus.COMPLETED, None)

    assert await asyncio.wait_for(reading, timeout=3) == [{"n": 1}]


async def test_the_latest_run_counts_its_events_and_reads_on_from_any_point(
    store: RunStore, user_id: UUID
):
    run_id = await store.create(user_id, "chat-1", "agent")
    for seq in (1, 2, 3):
        await store.append(run_id, seq, {"n": seq})
    await store.finish(run_id, AgentRunStatus.COMPLETED, None)

    assert await store.latest("chat-1") == (run_id, 3)
    assert await _read(store, run_id, 2) == [{"n": 3}]
    with pytest.raises(NotFound):
        await store.latest("chat-2")
