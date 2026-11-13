import json
from typing import override

import pytest
from a2a.server.tasks import InMemoryTaskStore
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

from src.app.a2a import Executable, add_executable_routes
from src.app.app import create_app
from src.app.container import Container
from src.core.config import AppSettings
from src.core.enums import Screen
from src.core.errors import ExecuteError
from src.core.types import NextStep
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
        AppSettings(),
    )
    return TestClient(app)


def _say(
    client: TestClient, text: str, task: dict | None = None, context: str | None = None
) -> dict:
    message = {"messageId": f"m-{text}", "role": "ROLE_USER", "parts": [{"text": text}]}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    if context:
        message |= {"contextId": context}
    response = client.post(
        "/ezcareer/a2a/greeter",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )
    return response.json()["result"]["task"]


def test_an_agent_takes_the_users_text_and_replies_in_text():
    model = ScriptedChatModel(replies=[AIMessage("Hello, Ada!")])

    task = _say(_agent_client(create_agent(model)), "Hi, I'm Ada")

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello, Ada!"
    assert model.requests[0][-1].text == "Hi, I'm Ada"


def test_an_agent_remembers_earlier_turns_in_the_same_context():
    model = ScriptedChatModel(
        replies=[AIMessage("Hello, Ada!"), AIMessage("Your name is Ada.")]
    )
    client = _agent_client(create_agent(model, checkpointer=InMemorySaver()))

    first = _say(client, "Hi, I'm Ada")
    second = _say(client, "What's my name?", context=first["contextId"])

    assert second["id"] != first["id"]
    assert [m.text for m in model.requests[1][-3:]] == [
        "Hi, I'm Ada",
        "Hello, Ada!",
        "What's my name?",
    ]


def test_an_agent_that_answers_with_a_structure_replies_in_data():
    model = ScriptedChatModel(
        replies=[
            AIMessage(
                "",
                tool_calls=[{"name": "Title", "args": {"title": "Dr"}, "id": "c1"}],
            )
        ]
    )

    task = _say(_agent_client(create_agent(model, response_format=Title)), "Title?")

    assert task["artifacts"][0]["parts"][0]["data"] == {"title": "Dr"}


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
    client = _agent_client(
        create_agent(model, tools=[ask_user], checkpointer=InMemorySaver())
    )

    asked = _say(client, "Greet me")

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == "Which title?"

    resumed = _say(client, "Dr", task=asked)

    assert resumed["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in resumed["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello, Dr Ada!"
    assert model.requests[-1][-1].text == "Dr"


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
    client = _agent_client(create_agent(_usage_model(), [title_of], name="job-analyst"))

    with client.stream(
        "POST",
        "/ezcareer/a2a/greeter",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendStreamingMessage",
            "params": {
                "message": {
                    "messageId": "m-1",
                    "role": "ROLE_USER",
                    "parts": [{"text": "Greet Ada"}],
                }
            },
        },
    ) as response:
        events = [
            json.loads(line.removeprefix("data: "))["result"]
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    working = [
        e["statusUpdate"]["status"]
        for e in events
        if "message" in e.get("statusUpdate", {}).get("status", {})
    ]
    assert {status["state"] for status in working} == {"TASK_STATE_WORKING"}
    assert _usages([status["message"] for status in working]) == USAGES


def test_a_blocking_runs_history_keeps_each_model_calls_usage():
    model = _usage_model()

    task = _say(_agent_client(create_agent(model, [title_of])), "Greet Ada")

    agent_messages = [m for m in task["history"] if m["role"] == "ROLE_AGENT"]
    assert len({m["messageId"] for m in agent_messages}) == len(agent_messages)
    assert _usages(agent_messages) == [usage | {"agent": "greeter"} for usage in USAGES]
