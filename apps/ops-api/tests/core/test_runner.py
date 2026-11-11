import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest

from src.clients.ezcareer import Completed, InputRequired, RunEvent, Started, Widget
from src.clients.ezcareer.schemas import Text
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.runner import Runner
from src.core.stores import AgentRunStatus, InMemoryRunStore

SETTINGS = EzcareerSettings(replay_ttl_seconds=60)


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


def _id(event: str) -> str:
    return next(line[4:] for line in event.splitlines() if line.startswith("id: "))


async def test_a_run_streams_each_event_with_its_id_and_a_retry_hint_first():
    runner = Runner(InMemoryRunStore(SETTINGS), retry_ms=2000)

    events = [
        e
        async for e in await runner.start_task(
            uuid4(), "chat-1", "agent", _events("1", "2")
        )
    ]

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
    runner = Runner(store, retry_ms=2000)

    for events in (paused(), replied(), _events("1")):
        [e async for e in await runner.start_task(uuid4(), "chat-1", "agent", events)]

    assert store.finished == [
        (AgentRunStatus.INPUT_REQUIRED, "task-1"),
        (AgentRunStatus.COMPLETED, "task-1"),
        (AgentRunStatus.FAILED, None),
    ]


async def test_a_thread_runs_one_turn_at_a_time():
    runner = Runner(InMemoryRunStore(SETTINGS), retry_ms=2000)
    release = asyncio.Event()
    await runner.start_task(uuid4(), "chat-1", "agent", _until(release))

    with pytest.raises(Conflict):
        await runner.start_task(uuid4(), "chat-1", "agent", _events("1"))
    release.set()


async def test_resume_skips_what_the_client_saw_and_refuses_another_runs_id():
    runner = Runner(InMemoryRunStore(SETTINGS), retry_ms=2000)
    events = [
        e
        async for e in await runner.start_task(
            uuid4(), "chat-1", "agent", _events("1", "2", "3")
        )
    ]

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
    runner = Runner(store, retry_ms=2000)
    await runner.start_task(uuid4(), "chat-1", "agent", _until(asyncio.Event()))
    await asyncio.sleep(0)

    await runner.aclose()

    assert store.finished == [(AgentRunStatus.CANCELLED, "task-1")]
    await runner.start_task(uuid4(), "chat-1", "agent", _events("1"))
