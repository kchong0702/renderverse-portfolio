import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import EzcareerSettings
from src.core.exceptions import NotFound
from tests.core.conftest import needs_postgres, postgres_store

pytestmark = needs_postgres


async def _collect(events: AsyncIterator[str]) -> list[str]:
    return [data async for data in events]


async def test_another_process_follows_a_run_live(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as writer,
        aclosing(postgres_store(engine, settings)) as reader,
    ):
        run_id = await writer.create(postgres_user, "chat-1")
        reading = asyncio.create_task(
            asyncio.wait_for(_collect(reader.read(run_id, 0)), timeout=2)
        )
        await asyncio.sleep(0.3)

        await writer.append(run_id, 1, '{"n":1}')
        await asyncio.sleep(0.3)
        await writer.append(run_id, 2, '{"n":2}')
        await writer.finish(run_id)

        assert await reading == ['{"n":1}', '{"n":2}']
        assert await reader.latest("chat-1") == (run_id, 2)


async def test_a_run_whose_writer_went_silent_ends_and_frees_its_key(
    engine: AsyncEngine, postgres_user: UUID
):
    async with aclosing(
        postgres_store(engine, EzcareerSettings(run_timeout_seconds=1))
    ) as runs:
        run_id = await runs.create(postgres_user, "chat-1")
        await runs.append(run_id, 1, '{"n":1}')
        await asyncio.sleep(1.2)

        assert await asyncio.wait_for(_collect(runs.read(run_id, 0)), timeout=3) == [
            '{"n":1}'
        ]
        with pytest.raises(NotFound):
            await runs.latest("chat-1")
        assert await runs.create(postgres_user, "chat-1") != run_id


async def test_two_processes_starting_the_same_chat_at_once_run_one_turn(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
    ):
        results = await asyncio.gather(
            first.create(postgres_user, "chat-1"),
            second.create(postgres_user, "chat-1"),
            return_exceptions=True,
        )

    assert sorted(type(result).__name__ for result in results) == ["Conflict", "str"]
