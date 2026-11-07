import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from src.app.a2a import Executable, add_executable_routes
from src.app.app import create_app
from src.app.container import Container
from src.core.config import AppSettings
from src.core.errors import ExecuteError

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
        input_schema=GreetInput,
        graph=_graph(),
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    add_executable_routes(
        app, [_executable()], AppSettings(public_url="https://box.example.ts.net")
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
