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
from src.core.errors import ExecuteError
from tests.conftest import ScriptedChatModel

PATH = "/ezcareer/a2a/greet"


class GreetInput(BaseModel):
    name: str


class GreetState(GreetInput):
    greeting: str = ""


def _greet(state: GreetState) -> dict:
    if state.name == "nobody":
        raise ExecuteError("Nobody to greet")
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
    assert task["artifacts"][0]["parts"][0]["text"] == "Hello, Ada!"
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
    assert resumed["artifacts"][0]["parts"][0]["text"] == "Hello, Dr Ada!"
    assert model.requests[-1][-1].text == "Dr"
