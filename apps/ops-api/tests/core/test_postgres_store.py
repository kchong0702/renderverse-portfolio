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
from src.clients.ezcareer import (
    Completed,
    EzcareerClient,
    MessageMetadata,
    RunEvent,
    TaskState,
)
from src.core.agent_runner import AgentRunner, ToolExecutor, Turn
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict
from src.core.stores import (
    AgentEvent,
    AgentRun,
    AgentRunStatus,
    RunLost,
    RunRecord,
)
from src.db.base import utcnow
from src.db.session import create_session_factory
from tests.core.conftest import needs_postgres, postgres_store

SENT = MessageMetadata(created_at=utcnow(), timezone="UTC")

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


async def test_a_run_whose_owner_went_quiet_stays_the_threads_current_run(
    engine: AsyncEngine, postgres_user: UUID
):
    async with aclosing(
        postgres_store(
            engine, EzcareerSettings(heartbeat_seconds=0.1, dead_after_seconds=0.5)
        )
    ) as runs:
        run_id = await runs.create(postgres_user, "chat-1", "agent")
        await runs.append(run_id, 1, {"n": 1})
        await asyncio.sleep(0.7)

        assert await runs.sweep() == []
        with pytest.raises(Conflict):
            await runs.create(postgres_user, "chat-1", "agent")
        assert await runs.latest("chat-1") == (run_id, 1)
        reading = asyncio.create_task(_collect(runs.read(run_id, 0)))
        await asyncio.sleep(0.3)
        assert not reading.done()

        await runs.finish(run_id, AgentRunStatus.COMPLETED, None)
        assert await asyncio.wait_for(reading, timeout=2) == [{"n": 1}]


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
        async def start(self, *args: object, **kwargs: object) -> str:
            """The task the message started"""
            return "task-1"

        async def follow(self, *args: object) -> AsyncIterator[RunEvent[Any]]:
            """A task that completes"""
            yield Completed(reply="Done.")

    async def nothing() -> None:
        """Nothing to prepare"""

    def as_is(turn: Turn, run_id: str, events: AsyncIterator[BaseModel]):
        return events

    set_actor(user_actor(postgres_user))
    factory = create_session_factory(engine)
    async with aclosing(postgres_store(engine, EzcareerSettings())) as runs:
        runner = AgentRunner(
            cast(EzcareerClient, _Harness()),
            ToolExecutor([], factory),
            runs,
            EzcareerSettings(),
        )
        await _collect(
            await runner.start(
                Turn(
                    user_id=postgres_user,
                    thread_id="chat-1",
                    agent="career-director",
                    metadata=None,
                    handle=as_is,
                ),
                message_id="m-1",
                sent=SENT,
                text="Hi",
                data=_Input(),
                prepare=nothing,
            )
        )

    async with factory() as session:
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


async def test_a_turn_whose_process_went_quiet_is_carried_on_by_another(
    engine: AsyncEngine, postgres_user: UUID
):
    class _Quiet:
        def __init__(self):
            """Starts a task and follows it until ops-api stops following"""
            self.stopped = False

        async def start(self, *args: object, **kwargs: object) -> str:
            return "task-1"

        async def follow(self, *args: object) -> AsyncIterator[RunEvent[Any]]:
            try:
                await asyncio.Event().wait()
            finally:
                self.stopped = True
            yield Completed(reply="never")

    class _Done:
        def __init__(self):
            """Finds the task completed, noting each task it is asked about"""
            self.asked: list[str | None] = []

        async def state(
            self, executable: str, task_id: str | None, *args: object
        ) -> TaskState:
            self.asked.append(task_id)
            return TaskState(task_id="task-1", events=[Completed(reply="Done.")])

    async def nothing() -> None:
        """Nothing to prepare"""

    def as_is(turn: Turn, run_id: str, events: AsyncIterator[BaseModel]):
        return events

    def turn(run: object = None) -> Turn:
        return Turn(
            user_id=postgres_user,
            thread_id="chat-1",
            agent="career-director",
            metadata=None,
            handle=as_is,
        )

    async def turn_of(run: RunRecord) -> Turn:
        return turn()

    set_actor(user_actor(postgres_user))
    factory = create_session_factory(engine)
    settings = EzcareerSettings(
        heartbeat_seconds=0.1,
        dead_after_seconds=0.5,
        sweep_seconds=0.1,
        reconnect_initial_wait_seconds=0.01,
        reconnect_max_wait_seconds=0.02,
    )
    quiet, done = _Quiet(), _Done()
    async with (
        aclosing(postgres_store(engine, settings)) as first_runs,
        aclosing(postgres_store(engine, settings)) as second_runs,
    ):
        first = AgentRunner(
            cast(EzcareerClient, quiet),
            ToolExecutor([], factory),
            first_runs,
            settings,
        )
        second = AgentRunner(
            cast(EzcareerClient, done),
            ToolExecutor([], factory),
            second_runs,
            settings,
        )
        await first.start(
            turn(),
            message_id="m-1",
            text="Hi",
            sent=SENT,
            data=_Input(),
            prepare=nothing,
        )
        await asyncio.sleep(0.7)

        await second.recover(turn_of)
        await asyncio.sleep(0.3)
        statuses = [
            e.split('"status":"')[1].split('"')[0]
            async for e in await second.resume("chat-1", None)
        ]
        await first.recover(turn_of)
        await asyncio.sleep(0.3)
        stopped = quiet.stopped
        await first.aclose()
        await second.aclose()

    async with factory() as session:
        run = await session.scalar(
            select(AgentRun).where(AgentRun.thread_id == "chat-1")
        )
    assert statuses == ["started", "reconnecting", "reconnected", "completed"]
    assert done.asked == ["task-1"]
    assert stopped
    assert run is not None
    assert (run.status, run.task_id) == (AgentRunStatus.COMPLETED, "task-1")


async def test_a_run_whose_owner_beats_is_left_alone(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings(heartbeat_seconds=0.1, dead_after_seconds=0.5)
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
    ):
        run_id = await first.create(postgres_user, "chat-1", "agent")
        for _ in range(4):
            await asyncio.sleep(0.2)
            assert run_id in await first.heartbeat()
            assert await second.sweep() == []
            assert await first.sweep() == []

        await first.append(run_id, 1, {"n": 1})


async def test_another_process_takes_over_a_quiet_run_and_its_owner_loses_it(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings(heartbeat_seconds=0.1, dead_after_seconds=0.5)
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
    ):
        run_id = await first.create(postgres_user, "chat-1", "agent")
        await first.set_task(run_id, "task-1")
        await first.append(run_id, 1, {"n": 1})
        done = await first.create(postgres_user, "chat-2", "agent")
        await first.finish(done, AgentRunStatus.COMPLETED, None)
        await asyncio.sleep(0.7)

        [taken] = await second.sweep()

        assert (taken.id, taken.thread_id, taken.task_id, taken.events) == (
            run_id,
            "chat-1",
            "task-1",
            1,
        )
        assert run_id not in await first.heartbeat()
        assert run_id in await second.heartbeat()
        with pytest.raises(RunLost):
            await first.append(run_id, 2, {"n": "stale"})
        with pytest.raises(RunLost):
            await first.set_task(run_id, "task-2")
        with pytest.raises(RunLost):
            await first.finish(run_id, AgentRunStatus.FAILED, None)
        await second.append(run_id, 2, {"n": 2})
        await second.finish(run_id, AgentRunStatus.COMPLETED, "task-1")

        assert await _collect(second.read(run_id, 0)) == [{"n": 1}, {"n": 2}]
        assert await second.paused("chat-1") is None
        assert await first.create(postgres_user, "chat-1", "agent") != run_id


async def test_two_processes_sweeping_at_once_take_a_quiet_run_over_once(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings(heartbeat_seconds=0.1, dead_after_seconds=0.5)
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
        aclosing(postgres_store(engine, settings)) as third,
    ):
        run_id = await first.create(postgres_user, "chat-1", "agent")
        await asyncio.sleep(0.7)

        swept = await asyncio.gather(second.sweep(), third.sweep())

    assert sorted([run.id for run in runs] for runs in swept) == [[], [run_id]]


async def test_a_run_released_on_shutdown_is_taken_over_at_once(
    engine: AsyncEngine, postgres_user: UUID
):
    settings = EzcareerSettings()
    async with (
        aclosing(postgres_store(engine, settings)) as first,
        aclosing(postgres_store(engine, settings)) as second,
    ):
        run_id = await first.create(postgres_user, "chat-1", "agent")
        assert await second.sweep() == []

        await first.release()

        assert [run.id for run in await second.sweep()] == [run_id]
