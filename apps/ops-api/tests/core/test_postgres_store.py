import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.app.actor import set_actor, user_actor
from src.clients.ezcareer import Completed, EzcareerClient, RunEvent, Started
from src.core.agent_runner import AgentRunner, ToolExecutor
from src.core.config import EzcareerSettings
from src.core.exceptions import NotFound
from src.core.stores import AgentEvent, AgentRun, AgentRunStatus
from src.db.session import create_session_factory
from tests.core.conftest import needs_postgres, postgres_store

pytestmark = needs_postgres


class _Input(BaseModel):
    pass


async def _collect[T](events: AsyncIterator[T]) -> list[T]:
    return [data async for data in events]


async def test_another_process_follows_a_run_live(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as writer,
        aclosing(postgres_store(engine, settings)) as reader,
    ):
        run_id = await writer.create(postgres_user, "chat-1", "agent")
        reading = asyncio.create_task(
            asyncio.wait_for(_collect(reader.read(run_id, 0)), timeout=2)
        )
        await asyncio.sleep(0.3)

        await writer.append(run_id, 1, {"n": 1})
        await asyncio.sleep(0.3)
        await writer.append(run_id, 2, {"n": 2})
        await writer.finish(run_id, AgentRunStatus.COMPLETED, None)

        assert await reading == [{"n": 1}, {"n": 2}]
        assert await reader.latest("chat-1") == (run_id, 2)


async def test_a_reader_listens_again_after_its_connection_drops(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as writer,
        aclosing(postgres_store(engine, settings)) as reader,
    ):
        first = await writer.create(postgres_user, "chat-1", "agent")
        await writer.finish(first, AgentRunStatus.COMPLETED, None)
        await _collect(reader.read(first, 0))
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE datname = current_database() AND query LIKE 'LISTEN%'"
                )
            )
        await asyncio.sleep(0.3)

        run_id = await writer.create(postgres_user, "chat-1", "agent")
        reading = asyncio.create_task(
            asyncio.wait_for(_collect(reader.read(run_id, 0)), timeout=2)
        )
        await asyncio.sleep(0.3)
        await writer.append(run_id, 1, {"n": 1})
        await writer.finish(run_id, AgentRunStatus.COMPLETED, None)

        assert await reading == [{"n": 1}]


async def test_a_run_whose_writer_went_silent_ends_and_frees_its_key(
    engine: AsyncEngine, postgres_user: UUID
):
    async with aclosing(
        postgres_store(engine, EzcareerSettings(run_timeout_seconds=1))
    ) as runs:
        run_id = await runs.create(postgres_user, "chat-1", "agent")
        await runs.append(run_id, 1, {"n": 1})
        await asyncio.sleep(1.2)

        assert await asyncio.wait_for(_collect(runs.read(run_id, 0)), timeout=3) == [
            {"n": 1}
        ]
        with pytest.raises(NotFound):
            await runs.latest("chat-1")
        assert await runs.create(postgres_user, "chat-1", "agent") != run_id


async def test_two_processes_starting_the_same_chat_at_once_run_one_turn(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
    ):
        results = await asyncio.gather(
            first.create(postgres_user, "chat-1", "agent"),
            second.create(postgres_user, "chat-1", "agent"),
            return_exceptions=True,
        )

    assert sorted(type(result).__name__ for result in results) == ["Conflict", "str"]


async def test_a_run_keeps_its_agent_task_status_and_events_as_its_user(
    engine: AsyncEngine, postgres_user: UUID
):
    class _Harness:
        def stream(
            self, *args: object, **kwargs: object
        ) -> AsyncIterator[RunEvent[Any]]:
            """A run that starts and completes"""
            return events()

    async def events() -> AsyncIterator[RunEvent[Any]]:
        yield Started(task_id="task-1")
        yield Completed(reply="Done.")

    set_actor(user_actor(postgres_user))
    async with aclosing(postgres_store(engine, EzcareerSettings())) as runs:
        runner = AgentRunner(
            cast(EzcareerClient, _Harness()), ToolExecutor([]), runs, retry_ms=2000
        )
        await _collect(
            await runner.start(
                postgres_user,
                "chat-1",
                "career-director",
                str,
                data=_Input(),
                metadata=None,
            )
        )

    async with create_session_factory(engine)() as session:
        run = await session.scalar(
            select(AgentRun).where(AgentRun.thread_id == "chat-1")
        )
        stored = (
            await session.scalars(select(AgentEvent).order_by(AgentEvent.seq))
        ).all()
    assert run is not None
    assert (run.agent, run.task_id, run.status) == (
        "career-director",
        "task-1",
        AgentRunStatus.COMPLETED,
    )
    assert [e.data for e in stored] == [
        {"status": "started", "task_id": "task-1"},
        {"status": "completed", "reply": "Done."},
    ]
    assert {run.created_by, run.updated_by, *(e.created_by for e in stored)} == {
        f"user:{postgres_user}"
    }
