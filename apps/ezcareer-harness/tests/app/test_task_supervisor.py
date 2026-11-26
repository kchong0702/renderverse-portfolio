import asyncio
import threading
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, TypedDict

import pytest
from a2a.server.context import ServerCallContext
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import Task, TaskState, TaskStatus
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AnyMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph

from src.app.a2a import Executable, TaskSupervisor
from src.app.app import create_app
from src.app.container import Container
from src.core.config import TaskSettings
from src.infrastructure.stores import MemoryTaskOwners, MemoryThreadLock

PATH = "/ezcareer/a2a/steps"
HEADERS = {"A2A-Version": "1.0"}


class Steps(TypedDict, total=False):
    first: str
    second: str
    messages: Annotated[list[AnyMessage], add_messages]


class Crash(Exception):
    pass


def _graph(
    ran: list[str], stop: Literal["crash", "hang"] | threading.Event = "crash"
) -> CompiledStateGraph:
    """Two steps; the first time it runs, the second crashes, as a stopped process
    would leave it, hangs until cancelled, or waits for the event, then finishes"""

    def first(_: Steps) -> Steps:
        ran.append("first")
        return {"first": "done"}

    async def second(_: Steps) -> Steps:
        ran.append("second")
        if ran.count("second") == 1 and isinstance(stop, threading.Event):
            while not stop.is_set():
                await asyncio.sleep(0.01)
        elif ran.count("second") == 1:
            if stop == "hang":
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    ran.append("cancelled")
                    raise
            raise Crash
        return {"second": "done", "messages": [AIMessage("Done.")]}

    graph = StateGraph(Steps)
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    return graph.compile(checkpointer=InMemorySaver())


THREAD = {"configurable": {"thread_id": "thread-1"}}


def _run(graph: CompiledStateGraph, task_id: str) -> None:
    """Runs graph for the task on thread-1 until the second step crashes"""
    with pytest.raises(Crash):
        asyncio.run(graph.ainvoke({}, {**THREAD, "metadata": {"task_id": task_id}}))


def _orphan(graph: CompiledStateGraph, store: InMemoryTaskStore, age: timedelta):
    """Leaves task-1 working on thread-1, last changed age ago, the thread
    checkpointed after the first step"""
    _run(graph, "task-1")
    task = Task(
        id="task-1",
        context_id="thread-1",
        status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
    )
    task.status.timestamp.FromDatetime(datetime.now(UTC) - age)
    task.metadata.update({"executable": "steps", "run": {}})
    asyncio.run(store.save(task, ServerCallContext()))


def _app(
    graph: CompiledStateGraph,
    store: InMemoryTaskStore,
    rows: dict[str, tuple[str, datetime]],
    kind: Literal["agent", "workflow"] = "agent",
    settings: TaskSettings | None = None,
    threads: set[str] | None = None,
) -> tuple[FastAPI, TaskSupervisor]:
    """An app instance serving graph as kind over the shared store, task owner rows
    and held threads, as one more replica would"""
    container = Container()
    container.executables.override(
        providers.List(
            providers.Object(
                Executable(
                    name="steps", description="Runs two steps", graph=graph, kind=kind
                )
            )
        )
    )
    container.task_store.override(providers.Object(store))
    settings = settings or TaskSettings()
    supervisor = TaskSupervisor(MemoryTaskOwners(rows), settings)
    container.task_supervisor.override(providers.Object(supervisor))
    container.thread_lock.override(
        providers.Object(MemoryThreadLock(settings.thread_wait_seconds, threads))
    )
    return create_app(container), supervisor


def _get(client: TestClient, task_id: str = "task-1") -> dict:
    """The task, by GetTask"""
    return client.post(
        PATH,
        headers=HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "GetTask",
            "params": {"id": task_id},
        },
    ).json()["result"]


def _ended(client: TestClient, task_id: str = "task-1") -> dict:
    """The task once it stops working"""
    for _ in range(200):
        task = _get(client, task_id)
        if task["status"]["state"] != "TASK_STATE_WORKING":
            return task
        time.sleep(0.01)
    raise AssertionError(f"{task_id} never ended")


def _start(client: TestClient, context: str | None = None) -> str:
    """Starts a run, on the context when given, without waiting for it; returns its
    task id"""
    return client.post(
        PATH,
        headers=HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m-1",
                    "role": "ROLE_USER",
                    "parts": [{"text": "Go"}],
                    "metadata": {"created_at": "2026-11-20T09:30:00Z"},
                    **({"contextId": context} if context else {}),
                },
                "configuration": {"returnImmediately": True},
            },
        },
    ).json()["result"]["task"]["id"]


def _thread(task: dict) -> dict:
    """The config of the task's thread"""
    return {"configurable": {"thread_id": task["contextId"]}}


def _until(condition, what: str) -> None:
    """Waits for condition to hold"""
    for _ in range(300):
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError(f"never {what}")


def test_a_quiet_task_with_no_owner_resumes_from_its_last_checkpoint_at_startup():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    _orphan(graph, store, timedelta(minutes=1))

    with TestClient(_app(graph, store, rows)[0]) as client:
        task = _ended(client)

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"] == [{"text": "Done."}]
    assert ran == ["first", "second", "second"]
    assert graph.get_state(THREAD).values["second"] == "done"
    assert rows == {}


def test_a_task_with_no_owner_that_changed_just_now_is_left_until_it_goes_quiet():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    _orphan(graph, store, timedelta(seconds=1))

    with TestClient(_app(graph, store, rows)[0]) as client:
        task = _get(client)

    assert task["status"]["state"] == "TASK_STATE_WORKING"
    assert ran == ["first", "second"]
    assert rows == {}


def test_a_task_whose_owner_stopped_beating_is_taken_over_by_another_instance():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    rows = {"task-1": ("dead-pod", datetime.now(UTC) - timedelta(minutes=1))}
    _orphan(graph, store, timedelta(seconds=40))

    with TestClient(_app(graph, store, rows)[0]) as client:
        task = _ended(client)

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ran == ["first", "second", "second"]
    assert rows == {}


def test_a_task_whose_owner_still_beats_is_left_alone():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    rows = {"task-1": ("live-pod", datetime.now(UTC))}
    _orphan(graph, store, timedelta(minutes=1))

    with TestClient(_app(graph, store, rows)[0]) as client:
        task = _get(client)

    assert task["status"]["state"] == "TASK_STATE_WORKING"
    assert ran == ["first", "second"]
    assert rows["task-1"][0] == "live-pod"


def test_two_instances_sweeping_at_once_resume_a_dead_owners_task_once():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    rows = {"task-1": ("dead-pod", datetime.now(UTC) - timedelta(minutes=1))}
    _orphan(graph, store, timedelta(seconds=40))
    instances = [_app(graph, store, rows), _app(graph, store, rows)]

    async def race() -> Task | None:
        await asyncio.gather(
            *(
                supervisor.sweep(app.state.handlers, store)
                for app, supervisor in instances
            )
        )
        for _ in range(200):
            task = await store.get("task-1", ServerCallContext())
            if task and task.status.state != TaskState.TASK_STATE_WORKING:
                break
            await asyncio.sleep(0.01)
        for app, _ in instances:
            for handler in app.state.handlers.values():
                await handler.aclose()
        return task

    task = asyncio.run(race())

    assert task and task.status.state == TaskState.TASK_STATE_COMPLETED
    assert ran == ["first", "second", "second"]
    assert rows == {}


def test_a_run_whose_task_was_taken_over_stops_without_failing_the_task():
    ran: list[str] = []
    graph = _graph(ran, "hang")
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    app, supervisor = _app(
        graph,
        store,
        rows,
        settings=TaskSettings(heartbeat_seconds=0.02, sweep_seconds=0.02),
    )

    with TestClient(app) as client:
        task_id = _start(client)
        _until(lambda: "second" in ran, "reached the second step")
        rows[task_id] = ("other-pod", datetime.now(UTC))
        _until(lambda: "cancelled" in ran, "cancelled the run")
        time.sleep(0.1)
        task = _get(client, task_id)

    assert task["status"]["state"] == "TASK_STATE_WORKING"
    assert graph.get_state(_thread(task)).values["first"] == "done"
    assert rows[task_id][0] == "other-pod"
    assert supervisor.runs == {}


def test_a_run_that_finds_its_task_taken_over_as_it_ends_leaves_the_task_alone():
    ran: list[str] = []
    wake = threading.Event()
    graph = _graph(ran, wake)
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    app, supervisor = _app(graph, store, rows)

    with TestClient(app) as client:
        task_id = _start(client)
        _until(lambda: "second" in ran, "reached the second step")
        rows[task_id] = ("other-pod", datetime.now(UTC))
        wake.set()
        _until(lambda: not supervisor.runs, "gave the run up")
        time.sleep(0.1)
        task = _get(client, task_id)

    assert task["status"]["state"] == "TASK_STATE_WORKING"
    assert "artifacts" not in task
    assert graph.get_state(_thread(task)).values["first"] == "done"
    assert rows[task_id][0] == "other-pod"


def test_shutting_down_hands_running_tasks_to_the_next_sweep_without_waiting():
    ran: list[str] = []
    graph = _graph(ran, "hang")
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}

    with TestClient(_app(graph, store, rows)[0]) as client:
        task_id = _start(client)
        _until(lambda: "second" in ran, "reached the second step")
    released = rows[task_id][1]

    with TestClient(_app(graph, store, rows)[0]) as client:
        task = _ended(client, task_id)

    assert released < datetime.now(UTC) - timedelta(minutes=30)
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ran == ["first", "second", "cancelled", "second"]
    assert rows == {}


def test_a_task_left_working_too_long_fails_without_running_again():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    _orphan(graph, store, timedelta(minutes=20))

    with TestClient(_app(graph, store, {})[0]) as client:
        task = _ended(client)

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"] == [{"text": "The assistant restarted"}]
    assert ran == ["first", "second"]
    assert graph.get_state(THREAD).next == ("second",)


def test_a_task_whose_thread_ran_a_later_task_fails_without_running_again():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    _orphan(graph, store, timedelta(minutes=1))
    ran.clear()
    _run(graph, "task-2")

    with TestClient(_app(graph, store, {})[0]) as client:
        task = _ended(client)

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"] == [{"text": "The assistant restarted"}]
    assert ran == ["first", "second"]


def test_a_task_whose_run_finished_before_its_process_died_completes_with_its_reply():
    ran = ["second"]
    graph = _graph(ran)
    asyncio.run(graph.ainvoke({}, {**THREAD, "metadata": {"task_id": "task-1"}}))
    store = InMemoryTaskStore()
    task = Task(
        id="task-1",
        context_id="thread-1",
        status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
    )
    task.status.timestamp.FromDatetime(datetime.now(UTC) - timedelta(minutes=1))
    task.metadata.update({"executable": "steps", "run": {}})
    asyncio.run(store.save(task, ServerCallContext()))

    with TestClient(_app(graph, store, {})[0]) as client:
        ended = _ended(client)

    assert ended["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ended["artifacts"][0]["parts"] == [{"text": "Done."}]
    assert ran == ["second", "first", "second"]


def test_cancelling_a_running_turn_keeps_its_finished_steps_and_the_next_one_runs():
    ran: list[str] = []
    graph = _graph(ran, "hang")
    store = InMemoryTaskStore()

    with TestClient(_app(graph, store, {})[0]) as client:
        task_id = _start(client)
        _until(lambda: "second" in ran, "reached the second step")
        cancelled = client.post(
            PATH,
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "CancelTask",
                "params": {"id": task_id},
            },
        ).json()["result"]
        _until(lambda: "cancelled" in ran, "cancelled the run")
        kept = graph.get_state(_thread(cancelled))
        next_id = _start(client, cancelled["contextId"])
        done = _ended(client, next_id)

    assert cancelled["status"]["state"] == "TASK_STATE_CANCELED"
    assert kept.values["first"] == "done"
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ran == ["first", "second", "cancelled", "first", "second"]


def test_a_workflow_left_working_fails_since_no_caller_follows_it():
    ran: list[str] = []
    graph = _graph(ran)
    store = InMemoryTaskStore()
    _orphan(graph, store, timedelta(minutes=1))

    with TestClient(_app(graph, store, {}, "workflow")[0]) as client:
        task = _ended(client)

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"] == [{"text": "The assistant restarted"}]
    assert ran == ["first", "second"]


def test_a_task_with_no_checkpoint_fails_when_taken_over():
    graph = _graph([])
    store = InMemoryTaskStore()
    task = Task(
        id="task-1",
        context_id="thread-1",
        status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
    )
    task.status.timestamp.FromDatetime(datetime.now(UTC) - timedelta(minutes=1))
    task.metadata.update({"executable": "steps", "run": {}})
    asyncio.run(store.save(task, ServerCallContext()))

    with TestClient(_app(graph, store, {})[0]) as client:
        restarted = _ended(client)

    assert restarted["status"]["state"] == "TASK_STATE_FAILED"
    assert restarted["status"]["message"]["parts"] == [
        {"text": "The assistant restarted"}
    ]


def test_a_run_that_raises_leaves_no_checkpoints():
    graph = _graph([])
    container = Container()
    container.executables.override(
        providers.List(
            providers.Object(
                Executable(name="steps", description="Runs two steps", graph=graph)
            )
        )
    )

    with TestClient(create_app(container), raise_server_exceptions=False) as client:
        task = client.post(
            PATH,
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "SendMessage",
                "params": {
                    "message": {
                        "messageId": "m-1",
                        "role": "ROLE_USER",
                        "parts": [{"text": "Go"}],
                    }
                },
            },
        ).json()

    assert "error" in task or task["result"]["task"]["status"]["state"] == (
        "TASK_STATE_FAILED"
    )
    assert not graph.checkpointer.storage


def test_a_run_cancelled_without_unclaiming_its_task_loses_it_on_the_next_heartbeat():
    owners = MemoryTaskOwners()
    supervisor = TaskSupervisor(owners, TaskSettings())

    async def cancelled_elsewhere() -> None:
        async def run() -> None:
            await supervisor.claim("task-1")
            await asyncio.sleep(3600)

        running = asyncio.create_task(run())
        await asyncio.sleep(0)
        running.cancel()
        with suppress(asyncio.CancelledError):
            await running
        await supervisor.heartbeat(InMemoryTaskStore())

    asyncio.run(cancelled_elsewhere())

    assert not asyncio.run(owners.owns("task-1"))


def test_a_message_waits_while_another_instance_still_runs_its_thread():
    ran: list[str] = []
    wake = threading.Event()
    graph = _graph(ran, wake)
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    threads: set[str] = set()

    with (
        TestClient(_app(graph, store, rows, threads=threads)[0]) as first,
        TestClient(_app(graph, store, rows, threads=threads)[0]) as second,
    ):
        earlier_id = _start(first, "thread-1")
        _until(lambda: "second" in ran, "reached the second step")
        later_id = _start(second, "thread-1")
        time.sleep(0.3)
        waiting = [*ran]
        wake.set()
        later = _ended(second, later_id)
        earlier = _ended(first, earlier_id)

    assert waiting == ["first", "second"]
    assert earlier["status"]["state"] == "TASK_STATE_COMPLETED"
    assert later["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ran == ["first", "second", "first", "second"]
    assert graph.get_state(THREAD).metadata["task_id"] == later_id
    assert threads == set()


def test_a_message_fails_when_an_earlier_run_holds_its_thread_too_long():
    ran: list[str] = []
    wake = threading.Event()
    graph = _graph(ran, wake)
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    threads: set[str] = set()
    impatient = TaskSettings(thread_wait_seconds=0.1)

    with (
        TestClient(_app(graph, store, rows, threads=threads)[0]) as first,
        TestClient(
            _app(graph, store, rows, settings=impatient, threads=threads)[0]
        ) as second,
    ):
        earlier_id = _start(first, "thread-1")
        _until(lambda: "second" in ran, "reached the second step")
        later = _ended(second, _start(second, "thread-1"))
        wake.set()
        earlier = _ended(first, earlier_id)

    assert later["status"]["state"] == "TASK_STATE_FAILED"
    assert later["status"]["message"]["parts"] == [
        {"text": "An earlier message to the assistant is still running"}
    ]
    assert earlier["status"]["state"] == "TASK_STATE_COMPLETED"
    assert graph.get_state(THREAD).metadata["task_id"] == earlier_id


def test_a_run_cancelled_on_another_instance_stops_and_frees_its_thread():
    ran: list[str] = []
    graph = _graph(ran, "hang")
    store = InMemoryTaskStore()
    rows: dict[str, tuple[str, datetime]] = {}
    threads: set[str] = set()
    beating = TaskSettings(heartbeat_seconds=0.02)

    with (
        TestClient(
            _app(graph, store, rows, settings=beating, threads=threads)[0]
        ) as first,
        TestClient(_app(graph, store, rows, threads=threads)[0]) as second,
    ):
        cancelled_id = _start(first, "thread-1")
        _until(lambda: "second" in ran, "reached the second step")
        cancelled = second.post(
            PATH,
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "CancelTask",
                "params": {"id": cancelled_id},
            },
        ).json()["result"]
        _until(lambda: "cancelled" in ran, "stopped the cancelled run")
        later = _ended(second, _start(second, "thread-1"))
        time.sleep(0.1)
        stopped = _get(first, cancelled_id)

    assert cancelled["status"]["state"] == "TASK_STATE_CANCELED"
    assert stopped["status"]["state"] == "TASK_STATE_CANCELED"
    assert later["status"]["state"] == "TASK_STATE_COMPLETED"
    assert ran == ["first", "second", "cancelled", "first", "second"]
    assert rows == {}
