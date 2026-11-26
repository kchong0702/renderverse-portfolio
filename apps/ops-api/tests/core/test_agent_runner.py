import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from src.clients.ezcareer import (
    AgentRunFailed,
    Completed,
    EzcareerClient,
    Failed,
    HarnessUnreachable,
    InputRequired,
    MessageMetadata,
    Run,
    RunEvent,
    TaskState,
    ToolRequest,
    ToolsRequested,
    Widget,
)
from src.clients.ezcareer.schemas import NextScreen, Text
from src.core.agent_runner import AgentRunner, Tool, ToolError, ToolExecutor, Turn
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound, ServiceUnavailable
from src.core.stores import AgentRunStatus, InMemoryRunStore, RunLost, RunRecord
from src.db.base import utcnow

SETTINGS = EzcareerSettings(
    replay_ttl_seconds=60,
    reconnect_seconds=0.2,
    reconnect_initial_wait_seconds=0.01,
    reconnect_max_wait_seconds=0.02,
    heartbeat_seconds=0.01,
    sweep_seconds=0.01,
)


class _Input(BaseModel):
    pass


class _Shelf(BaseModel):
    books: list[str]


type _Step = RunEvent[str] | ToolsRequested | Exception


class _Harness:
    def __init__(self):
        """Scripts each subscribe's events and each state, recording what it is sent"""
        self.subscribed: list[list[_Step]] = []
        self.states: list[TaskState | None | Exception] = []
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self.cancelled: list[str] = []
        self.run: Run[Any] | None = None

    async def start(self, executable: str, **message: Any) -> str:
        self.sent.append(("start", message))
        return "task-1"

    async def answer(self, executable: str, **message: Any) -> str:
        self.sent.append(("answer", message))
        return message["task_id"]

    async def results(self, executable: str, **message: Any) -> str:
        self.sent.append(("results", message))
        return message["task_id"]

    async def subscribe(
        self, *args: object
    ) -> AsyncIterator[RunEvent[str] | ToolsRequested]:
        for step in self.subscribed.pop(0):
            if isinstance(step, Exception):
                raise step
            yield step

    async def state(
        self,
        executable: str,
        task_id: str | None,
        context_id: str,
        since: datetime | None,
    ) -> TaskState | None:
        self.sent.append(("state", {"task_id": task_id, "since": since}))
        state = self.states.pop(0)
        if isinstance(state, Exception):
            raise state
        return state

    async def cancel(self, executable: str, task_id: str, context_id: str) -> None:
        self.cancelled.append(task_id)

    async def send(self, *args: object, **kwargs: object) -> Run[Any]:
        assert self.run is not None
        return self.run


class _Finishes(InMemoryRunStore):
    def __init__(self):
        """Records each finish and release; left are runs the next sweep takes over,
        and taken are runs another process took over"""
        super().__init__(SETTINGS)
        self.finished: list[tuple[AgentRunStatus, str | None]] = []
        self.left: list[RunRecord] = []
        self.taken: set[str] = set()
        self.released = False

    async def append(self, run_id: str, seq: int, data: dict[str, Any]) -> None:
        if run_id in self.taken:
            raise RunLost(run_id)
        await super().append(run_id, seq, data)

    async def finish(
        self, run_id: str, status: AgentRunStatus, task_id: str | None
    ) -> None:
        self.finished.append((status, task_id))
        await super().finish(run_id, status, task_id)

    async def heartbeat(self) -> set[str]:
        return await super().heartbeat() - self.taken

    async def sweep(self) -> list[RunRecord]:
        left, self.left = self.left, []
        return left

    async def release(self) -> None:
        self.released = True


def _runner(
    harness: _Harness,
    factory: async_sessionmaker[AsyncSession],
    store: InMemoryRunStore | None = None,
) -> AgentRunner:
    """A runner over the scripted harness with one shelf tool"""

    async def shelf(user_id: object, request: BaseModel) -> _Shelf:
        return _Shelf(books=["Dune"])

    return AgentRunner(
        cast(EzcareerClient, harness),
        ToolExecutor([{"shelf": Tool(_Input, shelf)}], factory),
        store or InMemoryRunStore(SETTINGS),
        SETTINGS,
    )


def _as_is(
    turn: Turn, run_id: str, events: AsyncIterator[RunEvent[str]]
) -> AsyncIterator[BaseModel]:
    return events


def _turn(thread_id: str = "chat-1", handle=_as_is) -> Turn:
    return Turn(
        user_id=uuid4(),
        thread_id=thread_id,
        agent="agent",
        metadata=None,
        handle=handle,
    )


async def _nothing() -> None:
    """Nothing to prepare"""


async def _start(runner: AgentRunner, turn: Turn | None = None) -> AsyncIterator[str]:
    return await runner.start(
        turn or _turn(),
        message_id="m-1",
        text="Hi",
        sent=MessageMetadata(created_at=utcnow(), timezone="UTC"),
        data=_Input(),
        prepare=_nothing,
    )


async def _statuses(stream: AsyncIterator[str]) -> list[str]:
    return [
        e.partition("\n")[0].split('"status":"')[1].split('"')[0] async for e in stream
    ]


def _id(event: str) -> str:
    return next(line[4:] for line in event.splitlines() if line.startswith("id: "))


async def test_a_run_streams_each_event_with_its_id_and_a_retry_hint_first(factory):
    harness = _Harness()
    harness.subscribed = [[Text(turn="t", text="1"), Completed(reply="1")]]

    events = [e async for e in await _start(_runner(harness, factory))]

    run_id = _id(events[0]).partition(":")[0]
    assert events == [
        f'data: {{"status":"started","task_id":"task-1"}}\nid: {run_id}:1\nretry: 2000\n\n',
        f'data: {{"status":"text","turn":"t","text":"1"}}\nid: {run_id}:2\n\n',
        f'data: {{"status":"completed","reply":"1"}}\nid: {run_id}:3\n\n',
    ]
    [(kind, sent)] = harness.sent
    assert (kind, sent) == (
        "start",
        {
            "context_id": "chat-1",
            "message_id": "m-1",
            "text": "Hi",
            "sent": sent["sent"],
            "data": _Input(),
            "metadata": None,
        },
    )
    assert sent["sent"].timezone == "UTC"


async def test_a_run_ends_as_its_last_event_says_with_the_task_it_followed(factory):
    class _Card(BaseModel):
        status: str = "card"

    async def carded(
        turn: Turn, run_id: str, events: AsyncIterator[RunEvent[str]]
    ) -> AsyncIterator[BaseModel]:
        async for event in events:
            yield _Card() if isinstance(event, Completed) else event

    harness = _Harness()
    harness.subscribed = [
        [InputRequired(task_id="task-1", widget=Widget(label="Go?"))],
        [Completed(reply="Done.")],
        [Failed(reason="No.")],
        [Completed(reply="Done.")],
    ]
    store = _Finishes()
    runner = _runner(harness, factory, store)

    for turn in [_turn(), _turn(), _turn(), _turn(handle=carded)]:
        [e async for e in await _start(runner, turn)]

    assert store.finished == [
        (AgentRunStatus.INPUT_REQUIRED, "task-1"),
        (AgentRunStatus.COMPLETED, "task-1"),
        (AgentRunStatus.FAILED, "task-1"),
        (AgentRunStatus.INPUT_REQUIRED, "task-1"),
    ]


async def test_a_thread_runs_one_turn_at_a_time(factory):
    release = asyncio.Event()

    class _Waits(_Harness):
        async def subscribe(self, *args: object) -> AsyncIterator[RunEvent[str]]:
            await release.wait()
            yield Completed(reply="1")

    runner = _runner(_Waits(), factory)
    await _start(runner)

    with pytest.raises(Conflict):
        await _start(runner)
    release.set()


async def test_resume_skips_what_the_client_saw_and_refuses_another_runs_id(factory):
    harness = _Harness()
    harness.subscribed = [[Text(turn="t", text="1"), Completed(reply="1")]]
    runner = _runner(harness, factory)
    events = [e async for e in await _start(runner)]

    resumed = [e async for e in await runner.resume("chat-1", _id(events[1]))]

    assert resumed == [events[2]]
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "0123456789abcdef:1")
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "not-an-id")
    with pytest.raises(NotFound):
        await runner.resume("chat-2", None)


async def test_the_tools_a_task_asks_for_are_executed_and_their_results_sent(
    factory,
):
    harness = _Harness()
    harness.subscribed = [
        [
            ToolsRequested(
                task_id="task-1", requests=[("i-1", ToolRequest(execute_tool="shelf"))]
            )
        ],
        [Completed(reply="Dune.")],
    ]

    statuses = await _statuses(await _start(_runner(harness, factory)))

    assert statuses == ["started", "completed"]
    assert [(kind, message.get("results")) for kind, message in harness.sent] == [
        ("start", None),
        ("results", [("i-1", _Shelf(books=["Dune"]))]),
    ]


async def test_a_tool_that_raises_is_logged_and_answered_with_an_error_so_the_turn_ends(
    factory,
):
    async def broken(user_id: object, request: BaseModel) -> _Shelf:
        raise RuntimeError("The shelf table is gone")

    harness = _Harness()
    harness.subscribed = [
        [
            ToolsRequested(
                task_id="task-1", requests=[("i-1", ToolRequest(execute_tool="shelf"))]
            )
        ],
        [Completed(reply="I couldn't read your shelf.")],
    ]
    store = _Finishes()
    runner = AgentRunner(
        cast(EzcareerClient, harness),
        ToolExecutor([{"shelf": Tool(_Input, broken)}], factory),
        store,
        SETTINGS,
    )

    with capture_logs() as logs:
        statuses = await _statuses(await _start(runner))

    assert statuses == ["started", "completed"]
    assert [
        message["results"] for kind, message in harness.sent if kind == "results"
    ] == [[("i-1", ToolError(error="Ops failed to execute shelf"))]]
    assert store.finished == [(AgentRunStatus.COMPLETED, "task-1")]
    [failed] = [log for log in logs if log["event"] == "tool_failed"]
    assert (failed["tool"], failed["task_id"], failed["exc_info"]) == (
        "shelf",
        "task-1",
        True,
    )


async def test_a_dropped_stream_reconnects_and_follows_the_task_on(factory):
    harness = _Harness()
    harness.subscribed = [
        [Text(turn="t", text="Two "), HarnessUnreachable("stream broke")],
        [Completed(reply="Two fit.")],
    ]
    harness.states = [
        HarnessUnreachable("down"),
        TaskState(task_id="task-1", events=[]),
    ]

    events = [e async for e in await _start(_runner(harness, factory))]

    statuses = [e.split('"status":"')[1].split('"')[0] for e in events]
    assert statuses == [
        "started",
        "text",
        "reconnecting",
        "reconnecting",
        "reconnected",
        "completed",
    ]
    assert '"attempt":1' in events[2] and '"attempt":2' in events[3]
    assert '"retry_at":"' in events[2]
    assert [
        message["task_id"] for kind, message in harness.sent if kind == "state"
    ] == [
        "task-1",
        "task-1",
    ]


async def test_a_task_that_ended_while_ops_api_was_away_ends_the_run_as_it_did(
    factory,
):
    harness = _Harness()
    harness.subscribed = [[HarnessUnreachable("stream broke")]]
    harness.states = [TaskState(task_id="task-1", events=[Completed(reply="Done.")])]
    store = _Finishes()

    statuses = await _statuses(await _start(_runner(harness, factory, store)))

    assert statuses == ["started", "reconnecting", "reconnected", "completed"]
    assert store.finished == [(AgentRunStatus.COMPLETED, "task-1")]


async def test_a_pause_found_on_reconnecting_has_its_tools_executed(factory):
    harness = _Harness()
    harness.subscribed = [
        [HarnessUnreachable("stream broke")],
        [Completed(reply="Dune.")],
    ]
    harness.states = [
        TaskState(
            task_id="task-1",
            events=[
                ToolsRequested(
                    task_id="task-1",
                    requests=[("i-1", ToolRequest(execute_tool="shelf"))],
                )
            ],
        )
    ]

    statuses = await _statuses(await _start(_runner(harness, factory)))

    assert statuses == ["started", "reconnecting", "reconnected", "completed"]
    assert [kind for kind, _ in harness.sent] == ["start", "state", "results"]


async def test_a_message_the_harness_may_not_have_got_is_found_by_its_thread(
    factory,
):
    class _Lost(_Harness):
        async def start(self, executable: str, **message: Any) -> str:
            raise HarnessUnreachable("down")

    harness = _Lost()
    harness.states = [TaskState(task_id="task-7", events=[]), None]
    harness.subscribed = [[Completed(reply="Hi.")]]
    before = utcnow()

    statuses = await _statuses(await _start(_runner(harness, factory)))

    assert statuses == ["reconnecting", "reconnected", "started", "completed"]
    [(kind, asked)] = harness.sent
    assert (kind, asked["task_id"]) == ("state", None)
    assert asked["since"] >= before


async def test_a_task_the_harness_lost_fails_the_run(factory):
    harness = _Harness()
    harness.subscribed = [[HarnessUnreachable("stream broke")]]
    harness.states = [None]

    events = [e async for e in await _start(_runner(harness, factory))]

    assert events[-1].startswith(
        'data: {"status":"failed","reason":"The assistant lost this reply.'
    )


async def test_a_harness_gone_past_the_reconnect_window_fails_the_run_and_stops_its_task(
    factory,
):
    harness = _Harness()
    harness.subscribed = [[HarnessUnreachable("stream broke")]]
    harness.states = [HarnessUnreachable("down")] * 1000
    store = _Finishes()

    events = [e async for e in await _start(_runner(harness, factory, store))]

    assert events[-1].startswith(
        'data: {"status":"failed","reason":"The assistant stopped responding.'
        ' Send your message again."'
    )
    assert all('"status":"reconnecting"' in e for e in events[1:-1])
    assert len(events) > 3
    assert harness.cancelled == ["task-1"]
    assert store.finished == [(AgentRunStatus.ABANDONED, "task-1")]


class _Hangs(_Harness):
    def __init__(self):
        """Follows a task that never ends, noting when ops-api stops following it"""
        super().__init__()
        self.stopped = False

    async def subscribe(self, *args: object) -> AsyncIterator[RunEvent[str]]:
        try:
            await asyncio.Event().wait()
        finally:
            self.stopped = True
        yield Completed(reply="never")


async def test_closing_hands_each_running_turn_over_and_leaves_its_task_alone(
    factory,
):
    harness = _Hangs()
    store = _Finishes()
    runner = _runner(harness, factory, store)
    await _start(runner)
    await asyncio.sleep(0.01)

    await runner.aclose()

    assert harness.stopped
    assert store.finished == []
    assert store.released
    assert harness.cancelled == []
    with pytest.raises(Conflict):
        await _start(runner)


async def test_closing_waits_for_a_run_still_saving_its_end(factory):
    class _SlowFinish(_Finishes):
        async def finish(
            self, run_id: str, status: AgentRunStatus, task_id: str | None
        ) -> None:
            await InMemoryRunStore.finish(self, run_id, status, task_id)
            await asyncio.sleep(0.2)
            self.finished.append((status, task_id))

    harness = _Harness()
    harness.subscribed = [[Completed(reply="Done.")]]
    store = _SlowFinish()
    runner = _runner(harness, factory, store)
    [e async for e in await _start(runner)]

    await runner.aclose()

    assert store.finished == [(AgentRunStatus.COMPLETED, "task-1")]


async def test_a_run_another_process_took_over_stops_here_without_finishing(factory):
    harness = _Hangs()
    store = _Finishes()
    runner = _runner(harness, factory, store)
    await _start(runner)

    async def turn(run: RunRecord) -> Turn:
        return _turn()

    await runner.recover(turn)
    await asyncio.sleep(0.05)
    assert not harness.stopped

    store.taken = await store.heartbeat()
    await asyncio.sleep(0.05)

    assert harness.stopped
    assert store.finished == []
    assert harness.cancelled == []
    await runner.aclose()


async def test_a_write_refused_as_taken_over_stops_the_run_here_without_finishing(
    factory,
):
    harness = _Harness()
    harness.subscribed = [[Completed(reply="1")]]
    store = _Finishes()

    def taken(
        turn: Turn, run_id: str, events: AsyncIterator[RunEvent[str]]
    ) -> AsyncIterator[BaseModel]:
        store.taken.add(run_id)
        return events

    await _start(_runner(harness, factory, store), _turn(handle=taken))
    await asyncio.sleep(0.05)

    assert store.finished == []
    assert harness.cancelled == []


async def test_each_run_a_sweep_takes_over_is_followed_by_reaching_the_harness_again(
    factory,
):
    harness = _Harness()
    harness.states = [TaskState(task_id="task-1", events=[Completed(reply="Done.")])]
    store = _Finishes()
    run_id = await store.create(uuid4(), "chat-1", "agent")
    await store.append(run_id, 1, {"status": "started", "task_id": "task-1"})
    store.left = [
        RunRecord(
            id=run_id,
            user_id=uuid4(),
            thread_id="chat-1",
            agent="agent",
            task_id="task-1",
            started_at=utcnow(),
            events=1,
        )
    ]
    runner = _runner(harness, factory, store)
    recovered: list[str] = []

    async def turn(run: RunRecord) -> Turn:
        recovered.append(run.id)
        return _turn()

    await runner.recover(turn)
    await asyncio.sleep(0.05)

    assert recovered == [run_id]
    assert [kind for kind, _ in harness.sent] == ["state"]
    assert store.finished == [(AgentRunStatus.COMPLETED, "task-1")]
    assert await _statuses(await runner.resume("chat-1", f"{run_id}:1")) == [
        "reconnecting",
        "reconnected",
        "completed",
    ]
    await runner.aclose()


async def _run(harness: _Harness, run: Run[Any], factory) -> object:
    """What AgentRunner.run gives for a one-shot run of agent that ends as run"""
    harness.run = run
    return await _runner(harness, factory).run(
        uuid4(), "agent", str, data=_Input(), metadata=None
    )


async def test_a_completed_run_gives_its_reply(factory):
    assert await _run(_Harness(), Completed(reply="Drafted."), factory) == "Drafted."


async def test_a_failed_run_raises_its_reason_and_the_screen_that_would_help(factory):
    portfolio = NextScreen(label="Add a fact in Portfolio", screen="portfolio")

    with pytest.raises(AgentRunFailed) as failed:
        await _run(
            _Harness(), Failed(reason="No facts to draft from", next=portfolio), factory
        )

    assert (failed.value.message, failed.value.next) == (
        "No facts to draft from",
        portfolio,
    )


async def test_a_one_shot_run_that_asks_for_input_is_unavailable(factory):
    with pytest.raises(ServiceUnavailable, match="agent asked for input"):
        await _run(
            _Harness(),
            InputRequired(task_id="task-1", widget=Widget(label="Which?")),
            factory,
        )
