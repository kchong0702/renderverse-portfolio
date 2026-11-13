import asyncio
from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.clients.ezcareer import (
    Completed,
    EzcareerClient,
    InputRequired,
    RunEvent,
    Started,
    Widget,
)
from src.clients.ezcareer.schemas import Text
from src.core.agent_runner import AgentRunner, ToolExecutor
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.stores import AgentRunStatus, InMemoryRunStore

SETTINGS = EzcareerSettings(replay_ttl_seconds=60)


class _Input(BaseModel):
    pass


class _Harness:
    def __init__(self, *runs: AsyncIterator[RunEvent[Any]]):
        """Streams each run in turn, whatever it is asked"""
        self.runs = list(runs)

    def stream(self, *args: object, **kwargs: object) -> AsyncIterator[RunEvent[Any]]:
        """The next run's events"""
        return self.runs.pop(0)


class _Finishes(InMemoryRunStore):
    def __init__(self):
        super().__init__(SETTINGS)
        self.finished: list[tuple[AgentRunStatus, str | None]] = []

    async def finish(
        self, run_id: str, status: AgentRunStatus, task_id: str | None
    ) -> None:
        self.finished.append((status, task_id))
        await super().finish(run_id, status, task_id)


async def _events(*texts: str) -> AsyncIterator[RunEvent[Any]]:
    for text in texts:
        yield Text(turn="t", text=text)


async def _until(release: asyncio.Event) -> AsyncIterator[RunEvent[Any]]:
    yield Started(task_id="task-1")
    await release.wait()
    yield Text(turn="t", text="0")


def _runner(
    store: InMemoryRunStore, *runs: AsyncIterator[RunEvent[Any]]
) -> AgentRunner:
    """A runner over a harness that streams these runs, with no tools"""
    return AgentRunner(
        cast(EzcareerClient, _Harness(*runs)), ToolExecutor(), store, retry_ms=2000
    )


async def _start(runner: AgentRunner, thread_id: str) -> AsyncIterator[str]:
    """Start a run of agent on the thread"""
    return await runner.start(
        uuid4(), thread_id, "agent", str, data=_Input(), metadata=None
    )


def _id(event: str) -> str:
    return next(line[4:] for line in event.splitlines() if line.startswith("id: "))


async def test_a_run_streams_each_event_with_its_id_and_a_retry_hint_first():
    runner = _runner(InMemoryRunStore(SETTINGS), _events("1", "2"))

    events = [e async for e in await _start(runner, "chat-1")]

    run_id = _id(events[0]).partition(":")[0]
    assert events == [
        f'data: {{"status":"text","turn":"t","text":"1"}}\nid: {run_id}:1\nretry: 2000\n\n',
        f'data: {{"status":"text","turn":"t","text":"2"}}\nid: {run_id}:2\n\n',
    ]


async def test_a_run_ends_as_its_last_event_says_with_the_task_it_started():
    async def paused() -> AsyncIterator[RunEvent[Any]]:
        yield Started(task_id="task-1")
        yield InputRequired(task_id="task-1", widget=Widget(label="Go?"))

    async def replied() -> AsyncIterator[RunEvent[Any]]:
        yield Started(task_id="task-1")
        yield Completed(reply="Done.")

    store = _Finishes()
    runner = _runner(store, paused(), replied(), _events("1"))

    for _ in range(3):
        [e async for e in await _start(runner, "chat-1")]

    assert store.finished == [
        (AgentRunStatus.INPUT_REQUIRED, "task-1"),
        (AgentRunStatus.COMPLETED, "task-1"),
        (AgentRunStatus.FAILED, None),
    ]


async def test_a_handle_rewrites_the_events_the_run_keeps():
    async def shouted(
        events: AsyncIterator[RunEvent[Any]],
    ) -> AsyncIterator[BaseModel]:
        async for event in events:
            yield Text(turn="t", text=cast(Text, event).text.upper())

    runner = _runner(InMemoryRunStore(SETTINGS), _events("a", "b"))

    events = [
        e
        async for e in await runner.start(
            uuid4(),
            "chat-1",
            "agent",
            str,
            data=_Input(),
            metadata=None,
            handle=shouted,
        )
    ]

    assert [e.partition("\n")[0] for e in events] == [
        'data: {"status":"text","turn":"t","text":"A"}',
        'data: {"status":"text","turn":"t","text":"B"}',
    ]


async def test_a_thread_runs_one_turn_at_a_time():
    release = asyncio.Event()
    runner = _runner(InMemoryRunStore(SETTINGS), _until(release), _events("1"))
    await _start(runner, "chat-1")

    with pytest.raises(Conflict):
        await _start(runner, "chat-1")
    release.set()


async def test_resume_skips_what_the_client_saw_and_refuses_another_runs_id():
    runner = _runner(InMemoryRunStore(SETTINGS), _events("1", "2", "3"))
    events = [e async for e in await _start(runner, "chat-1")]

    resumed = [e async for e in await runner.resume("chat-1", _id(events[1]))]

    assert resumed == [events[2]]
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "0123456789abcdef:1")
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "not-an-id")
    with pytest.raises(NotFound):
        await runner.resume("chat-2", None)


async def test_closing_marks_each_running_turn_cancelled():
    store = _Finishes()
    runner = _runner(store, _until(asyncio.Event()), _events("1"))
    await _start(runner, "chat-1")
    await asyncio.sleep(0)

    await runner.aclose()

    assert store.finished == [(AgentRunStatus.CANCELLED, "task-1")]
    await _start(runner, "chat-1")
