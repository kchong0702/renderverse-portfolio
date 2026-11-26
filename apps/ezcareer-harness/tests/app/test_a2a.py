import asyncio
from typing import Any, override

import pytest
from a2a.server.context import ServerCallContext
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import Task, TaskState, TaskStatus
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from src.app.a2a import Executable, TaskSupervisor, add_executable_routes
from src.app.app import create_app
from src.app.container import Container
from src.core.config import AppSettings, TaskSettings
from src.core.enums import Screen
from src.core.errors import ExecuteError
from src.core.types import NextStep
from src.infrastructure.stores import MemoryTaskOwners, MemoryThreadLock
from tests.app import ops_api
from tests.conftest import ScriptedChatModel

PATH = "/ezcareer/a2a/greet"


class GreetInput(BaseModel):
    name: str


class GreetState(GreetInput):
    greeting: str = ""


def _greet(state: GreetState) -> dict:
    if state.name == "nobody":
        raise ExecuteError("Nobody to greet")
    if state.name == "stranger":
        raise ExecuteError(
            "Add your name first",
            NextStep(label="Add your name", screen=Screen.PORTFOLIO),
        )
    if state.name == "loop":
        return {}
    title = interrupt("Which title?") if state.name == "ask" else "Dr"
    return {"greeting": f"Hello, {title} {state.name}!"}


def _graph():
    graph = StateGraph(GreetState, input_schema=GreetInput)
    graph.add_node("greet", _greet)
    graph.add_edge(START, "greet")
    graph.add_conditional_edges("greet", lambda s: "greet" if s.name == "loop" else END)
    return graph.compile(checkpointer=InMemorySaver()).with_config(recursion_limit=5)


def _executable() -> Executable:
    return Executable(
        name="greet",
        description="Greets a person",
        graph=_graph(),
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    add_executable_routes(
        app,
        [_executable()],
        InMemoryTaskStore(),
        None,
        TaskSupervisor(MemoryTaskOwners(), TaskSettings()),
        MemoryThreadLock(60),
        AppSettings(public_url="https://box.example.ts.net"),
    )
    return TestClient(app)


def _send(client: TestClient, data: object = None, task: dict | None = None):
    message = {
        "messageId": f"m-{data}",
        "role": "ROLE_USER",
        "parts": [{"data": data}] if data is not None else [{"text": "hi"}],
    }
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    response = client.post(
        PATH,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )
    return response.json()["result"]["task"]


def _status_text(task: dict) -> str:
    return task["status"]["message"]["parts"][0]["text"]


def test_card_points_clients_at_the_executable(client: TestClient):
    card = client.get(f"{PATH}/.well-known/agent-card.json").json()

    assert card["name"] == "greet"
    assert card["supportedInterfaces"][0]["url"] == f"https://box.example.ts.net{PATH}"


def test_completed_run_returns_the_final_state_as_an_artifact(client: TestClient):
    task = _send(client, {"name": "Ada"})

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["data"] == {
        "name": "Ada",
        "greeting": "Hello, Dr Ada!",
    }


def test_execute_error_fails_the_task_with_its_reason(client: TestClient):
    task = _send(client, {"name": "nobody"})

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(task) == "Nobody to greet"


def test_a_failure_the_user_can_fix_carries_its_next_step(client: TestClient):
    task = _send(client, {"name": "stranger"})

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"] == [
        {"text": "Add your name first"},
        {"data": {"next": {"label": "Add your name", "screen": "portfolio"}}},
    ]


def test_an_execute_error_without_a_next_step_sends_only_its_reason(
    client: TestClient,
):
    task = _send(client, {"name": "nobody"})

    assert task["status"]["message"]["parts"] == [{"text": "Nobody to greet"}]


def test_recursion_limit_fails_the_task(client: TestClient):
    task = _send(client, {"name": "loop"})

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(task) == "Ran out of steps before finishing"


def test_invalid_input_fails_the_task(client: TestClient):
    task = _send(client)

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(task).startswith("Invalid input:")


def test_interrupt_asks_for_input_and_the_answer_resumes_the_run(
    client: TestClient,
):
    asked = _send(client, {"name": "ask"})

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == "Which title?"

    resumed = _send(client, "Prof", task=asked)

    assert resumed["status"]["state"] == "TASK_STATE_COMPLETED"
    assert resumed["artifacts"][0]["parts"][0]["data"]["greeting"] == (
        "Hello, Prof ask!"
    )


class Names(BaseModel):
    first: str = ""
    last: str = ""


def test_two_interrupts_at_once_resume_each_with_the_answer_under_its_id():
    graph = StateGraph(Names)
    graph.add_node("first", lambda _: {"first": interrupt({"ask": "first"})})
    graph.add_node("last", lambda _: {"last": interrupt({"ask": "last"})})
    graph.add_edge(START, "first")
    graph.add_edge(START, "last")
    app = FastAPI()
    add_executable_routes(
        app,
        [
            Executable(
                name="greet",
                description="Asks two names at once",
                graph=graph.compile(checkpointer=InMemorySaver()),
            )
        ],
        InMemoryTaskStore(),
        None,
        TaskSupervisor(MemoryTaskOwners(), TaskSettings()),
        MemoryThreadLock(60),
        AppSettings(public_url="https://box.example.ts.net"),
    )
    client = TestClient(app)
    asked = _send(client, {})
    ids = {
        part["data"]["ask"]: part["metadata"]["interrupt_id"]
        for part in asked["status"]["message"]["parts"]
    }

    resumed = client.post(
        PATH,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m-names",
                    "role": "ROLE_USER",
                    "taskId": asked["id"],
                    "contextId": asked["contextId"],
                    "parts": [
                        {"data": "Lovelace", "metadata": {"interrupt_id": ids["last"]}},
                        {"data": "Ada", "metadata": {"interrupt_id": ids["first"]}},
                    ],
                }
            },
        },
    ).json()["result"]["task"]

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert len(set(ids.values())) == 2
    assert resumed["artifacts"][0]["parts"][0]["data"] == {
        "first": "Ada",
        "last": "Lovelace",
    }


def _served(graph: CompiledStateGraph, store: InMemoryTaskStore) -> TestClient:
    """A client of graph served as the greet workflow over store"""
    app = FastAPI()
    add_executable_routes(
        app,
        [Executable(name="greet", description="Greets a person", graph=graph)],
        store,
        None,
        TaskSupervisor(MemoryTaskOwners(), TaskSettings()),
        MemoryThreadLock(60),
        AppSettings(public_url="https://box.example.ts.net"),
    )
    return TestClient(app)


def test_a_bare_answer_with_no_question_waiting_fails_the_task():
    graph = _graph()
    graph.invoke(
        {"name": "Ada"},
        {"configurable": {"thread_id": "task-1"}, "metadata": {"task_id": "task-1"}},
    )
    store = InMemoryTaskStore()
    paused = Task(
        id="task-1",
        context_id="context-1",
        status=TaskStatus(state=TaskState.TASK_STATE_INPUT_REQUIRED),
    )
    paused.metadata.update({"executable": "greet", "run": {}})
    asyncio.run(store.save(paused, ServerCallContext()))

    answered = _send(
        _served(graph, store), "Prof", task={"id": "task-1", "contextId": "context-1"}
    )

    assert answered["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(answered) == "There is no question waiting for an answer"


class Found(BaseModel):
    documents: str = ""
    title: str = ""


def test_a_mixed_pause_lists_the_users_question_first_and_a_bare_answer_goes_to_it():
    graph = StateGraph(Found)
    graph.add_node(
        "data_request",
        lambda _: {"documents": interrupt({"execute_tool": "documents"})},
    )
    graph.add_node("question", lambda _: {"title": interrupt({"ask": "title"})})
    graph.add_edge(START, "data_request")
    graph.add_edge(START, "question")
    client = _served(graph.compile(checkpointer=InMemorySaver()), InMemoryTaskStore())

    asked = _send(client, {})
    answered = _send(client, "Dr", task=asked)

    assert [part["data"] for part in asked["status"]["message"]["parts"]] == [
        {"ask": "title"},
        {"execute_tool": "documents"},
    ]
    assert answered["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert [part["data"] for part in answered["status"]["message"]["parts"]] == [
        {"execute_tool": "documents"}
    ]


def test_the_app_serves_the_containers_executables():
    container = Container()
    container.executables.override(providers.List(providers.Object(_executable())))

    card = TestClient(create_app(container)).get(f"{PATH}/.well-known/agent-card.json")

    assert card.json()["name"] == "greet"


def test_the_app_keeps_tasks_in_the_containers_task_store():
    saved: list[str] = []

    class RecordingStore(InMemoryTaskStore):
        @override
        async def save(self, task, context) -> None:
            saved.append(task.id)
            await super().save(task, context)

    container = Container()
    container.executables.override(providers.List(providers.Object(_executable())))
    container.task_store.override(providers.Singleton(RecordingStore))

    task = _send(TestClient(create_app(container)), {"name": "Ada"})

    assert task["id"] in saved


class Title(BaseModel):
    title: str


AGENT = "/ezcareer/a2a/greeter"
STAMPED = "[Fri 20 Nov 2026, 09:30 Europe/London] Hi, I'm Ada"


def _agent(model: ScriptedChatModel, **kwargs: Any) -> CompiledStateGraph:
    """A plain agent on model that keeps its threads in memory"""
    return create_agent(model, checkpointer=InMemorySaver(), **kwargs)


def _agent_client(agent: CompiledStateGraph) -> TestClient:
    app = FastAPI()
    add_executable_routes(
        app,
        [
            Executable(
                kind="agent",
                name="greeter",
                description="Greets whoever writes to it",
                graph=agent,
            )
        ],
        InMemoryTaskStore(),
        None,
        TaskSupervisor(MemoryTaskOwners(), TaskSettings()),
        MemoryThreadLock(60),
        AppSettings(),
    )
    return TestClient(app)


def _rpc(client: TestClient, method: str, task_id: str) -> dict:
    """The task GetTask or CancelTask returns"""
    return client.post(
        AGENT,
        headers={"A2A-Version": "1.0"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": {"id": task_id}},
    ).json()["result"]


def test_an_agent_takes_the_users_text_and_replies_in_text():
    model = ScriptedChatModel(replies=[AIMessage("Hello, Ada!")])

    task = ops_api.send(_agent_client(_agent(model)), AGENT, [{"text": "Hi, I'm Ada"}])

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello, Ada!"
    assert [m.text for m in model.requests[0]] == [STAMPED]


def test_the_users_message_is_stamped_in_their_zone_under_its_a2a_id():
    agent = _agent(ScriptedChatModel(replies=[AIMessage("Hello, Ada!")]))
    message = {
        "messageId": "m-ada",
        "role": "ROLE_USER",
        "contextId": "thread-1",
        "parts": [{"text": "Hi, I'm Ada"}],
        "metadata": {
            "created_at": "2026-11-21T01:05:00Z",
            "timezone": "Asia/Singapore",
        },
    }

    _agent_client(agent).post(
        AGENT,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )

    [sent, _] = agent.get_state({"configurable": {"thread_id": "thread-1"}}).values[
        "messages"
    ]
    assert sent.id == "m-ada"
    assert sent.text == "[Sat 21 Nov 2026, 09:05 Asia/Singapore] Hi, I'm Ada"


def test_a_users_message_without_when_it_was_sent_fails():
    client = _agent_client(_agent(ScriptedChatModel(replies=[])))

    task = client.post(
        AGENT,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m-1",
                    "role": "ROLE_USER",
                    "parts": [{"text": "Hi"}],
                }
            },
        },
    ).json()["result"]["task"]

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"][0]["text"].startswith("Invalid input:")


def test_an_agent_keeps_its_threads_state_across_turns_under_the_context_id():
    model = ScriptedChatModel(
        replies=[AIMessage("Hello, Ada!"), AIMessage("Your name is Ada.")]
    )
    agent = _agent(model)
    client = _agent_client(agent)

    first = ops_api.send(client, AGENT, [{"text": "Hi, I'm Ada"}], context="thread-1")
    second = ops_api.send(
        client, AGENT, [{"text": "What's my name?"}], context="thread-1"
    )

    assert second["id"] != first["id"]
    assert [m.text for m in model.requests[1]] == [
        STAMPED,
        "Hello, Ada!",
        "[Fri 20 Nov 2026, 09:30 Europe/London] What's my name?",
    ]
    assert (
        agent.get_state({"configurable": {"thread_id": "thread-1"}})
        .values["messages"][-1]
        .text
        == "Your name is Ada."
    )


def test_each_turn_ends_with_the_agents_message_by_its_id_in_the_thread():
    agent = _agent(ScriptedChatModel(replies=[AIMessage("Hello, Ada!")]))
    client = _agent_client(agent)

    task = ops_api.send(client, AGENT, [{"text": "Hi, I'm Ada"}], context="thread-1")
    again = _rpc(client, "GetTask", task["id"])

    message = task["status"]["message"]
    [_, reply] = agent.get_state({"configurable": {"thread_id": "thread-1"}}).values[
        "messages"
    ]
    assert message["role"] == "ROLE_AGENT"
    assert message["parts"] == [{"text": "Hello, Ada!"}]
    assert message["messageId"] == reply.id
    assert again["status"]["message"]["messageId"] == message["messageId"]


def test_an_agent_that_answers_with_a_structure_replies_in_data():
    model = ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[{"name": "Title", "args": {"title": "Dr"}, "id": "c1"}],
            )
        ]
    )

    task = ops_api.send(
        _agent_client(_agent(model, response_format=Title)),
        AGENT,
        [{"text": "Title?"}],
    )

    assert task["artifacts"][0]["parts"][0]["data"] == {"title": "Dr"}


def test_an_agent_turn_that_ends_without_reply_text_fails():
    model = ScriptedChatModel(
        replies=[AIMessage([{"type": "text", "text": "", "phase": "final_answer"}])]
    )

    task = ops_api.send(_agent_client(_agent(model)), AGENT, [{"text": "Hi"}])

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(task) == "The assistant stopped without replying"
    assert not [a for a in task.get("artifacts", []) if a["name"] == "greeter"]


@tool
def ask_user(question: str) -> str:
    """Asks the user a question and returns their answer"""
    return interrupt(question)


def test_a_served_agent_asks_the_user_and_resumes_on_the_same_task():
    model = ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": "ask_user",
                        "args": {"question": "Which title?"},
                        "id": "c1",
                    }
                ],
            ),
            AIMessage("Hello, Dr Ada!"),
        ]
    )
    client = _agent_client(_agent(model, tools=[ask_user]))

    asked = ops_api.send(client, AGENT, [{"text": "Greet me"}])

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == "Which title?"

    resumed = ops_api.send(client, AGENT, [{"text": "Dr"}], task=asked)

    assert resumed["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in resumed["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello, Dr Ada!"
    assert model.requests[-1][-1].text == "Dr"


def test_the_next_message_after_a_cancelled_pause_drops_the_paused_step_and_runs():
    model = ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": "ask_user",
                        "args": {"question": "Which title?"},
                        "id": "c1",
                    }
                ],
            ),
            AIMessage("Hello, Ada!"),
        ]
    )
    agent = _agent(model, tools=[ask_user], middleware=[PatchToolCallsMiddleware()])
    client = _agent_client(agent)
    thread = {"configurable": {"thread_id": "thread-1"}}

    asked = ops_api.send(client, AGENT, [{"text": "Greet me"}], context="thread-1")
    cancelled = _rpc(client, "CancelTask", asked["id"])
    paused = agent.get_state(thread)
    done = ops_api.send(client, AGENT, [{"text": "Hi, I'm Ada"}], context="thread-1")

    assert cancelled["status"]["state"] == "TASK_STATE_CANCELED"
    assert paused.next == ("tools",)
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert agent.get_state(thread).next == ()
    [*_, call, patched, sent] = model.requests[-1]
    assert call.tool_calls[0]["id"] == patched.tool_call_id == "c1"
    assert sent.text == STAMPED


@tool
def title_of(name: str) -> str:
    """Looks up the title of the person called name"""
    return "Dr"


def _usage_model() -> ScriptedChatModel:
    return ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[{"name": "title_of", "args": {"name": "Ada"}, "id": "c1"}],
                usage_metadata={
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                    "input_token_details": {"cache_read": 100, "cache_creation": 10},
                    "output_token_details": {"reasoning": 12},
                },
                response_metadata={"stop_reason": "tool_use", "id": "msg_1"},
            ),
            AIMessage("Hello, Dr Ada!"),
        ]
    )


def _usages(messages: list[dict]) -> list[dict]:
    """The usage of every model call the messages report, without its latency"""
    usages = [
        part["data"]["usage"]
        for message in messages
        for part in message["parts"]
        if "usage" in part.get("data", {})
    ]
    assert all(usage.pop("latency_ms") >= 0 for usage in usages)
    return usages


USAGES = [
    {
        "provider": "glm",
        "model": "glm-5.3",
        "agent": "job-analyst",
        "node": "model",
        "input_tokens": 120,
        "output_tokens": 30,
        "cache_read_tokens": 100,
        "cache_write_tokens": 10,
        "reasoning_tokens": 12,
        "stop_reason": "tool_use",
        "request_id": "msg_1",
    },
    {
        "provider": "glm",
        "model": "glm-5.3",
        "agent": "job-analyst",
        "node": "model",
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "stop_reason": None,
        "request_id": None,
    },
]


def test_a_streamed_run_reports_each_model_calls_usage_as_it_ends():
    model = _usage_model()
    client = _agent_client(_agent(model, tools=[title_of], name="job-analyst"))

    events = ops_api.stream(client, AGENT, [{"text": "Greet Ada"}])

    working = [
        e["statusUpdate"]["status"]
        for e in events
        if e.get("statusUpdate", {}).get("status", {}).get("state")
        == "TASK_STATE_WORKING"
        and "message" in e["statusUpdate"]["status"]
    ]
    assert _usages([status["message"] for status in working]) == USAGES


def test_a_blocking_runs_history_keeps_each_model_calls_usage():
    model = _usage_model()

    task = ops_api.send(
        _agent_client(_agent(model, tools=[title_of])),
        AGENT,
        [{"text": "Greet Ada"}],
    )

    agent_messages = [m for m in task["history"] if m["role"] == "ROLE_AGENT"]
    assert len({m["messageId"] for m in agent_messages}) == len(agent_messages)
    assert _usages(agent_messages) == [usage | {"agent": "greeter"} for usage in USAGES]


@pytest.mark.parametrize("by_id", [False, True])
def test_answering_a_question_a_newer_message_replaced_fails_the_task(by_id: bool):
    model = ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": "ask_user",
                        "args": {"question": "Which title?"},
                        "id": "c1",
                    }
                ],
            ),
            AIMessage("Hello, Ada!"),
        ]
    )
    agent = _agent(model, tools=[ask_user], middleware=[PatchToolCallsMiddleware()])
    client = _agent_client(agent)
    asked = ops_api.send(client, AGENT, [{"text": "Greet me"}], context="thread-1")
    [question] = asked["status"]["message"]["parts"]
    newer = ops_api.send(client, AGENT, [{"text": "Hi, I'm Ada"}], context="thread-1")

    answered = ops_api.send(
        client,
        AGENT,
        [{"data": "Dr", "metadata": question["metadata"]} if by_id else {"text": "Dr"}],
        task=asked,
    )

    assert newer["status"]["state"] == "TASK_STATE_COMPLETED"
    assert answered["status"]["state"] == "TASK_STATE_FAILED"
    assert _status_text(answered) == "This question was replaced by a newer message"
    assert len(model.requests) == 2
