import json

import httpx2
import pytest
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from pydantic import JsonValue

from src.agents import Agent, build_agent
from src.app.a2a import Executable, add_executable_routes
from src.core.config import AppSettings
from tests.agents.test_builder import GREETER
from tests.conftest import ScriptedChatModel

PATH = "/ezcareer/a2a/greeter"
SERVER_KEY = "sk-ant-server-0123456789abcdef"
METADATA = {"model": {"family": "claude", "model": "claude-sonnet-5-5"}}


class FakeAnthropic:
    def __init__(self) -> None:
        """Answers every Messages API call with one text reply, keeping each request"""
        self.requests: list[httpx2.Request] = []

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Records the request and streams one text reply as Claude would"""
        self.requests.append(request)
        message = {
            "id": "msg-1",
            "type": "message",
            "role": "assistant",
            "model": json.loads(request.content)["model"],
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        events = [
            {"type": "message_start", "message": message},
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Hello from Claude"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
            {"type": "message_stop"},
        ]
        return httpx2.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content="".join(
                f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events
            ),
        )


@pytest.fixture
def anthropic(monkeypatch: pytest.MonkeyPatch) -> FakeAnthropic:
    """Every outgoing LLM call lands on a fake Anthropic, on the server's key"""
    fake = FakeAnthropic()
    monkeypatch.setenv("ANTHROPIC_API_KEY", SERVER_KEY)
    monkeypatch.setattr(
        httpx2.AsyncHTTPTransport, "handle_async_request", fake.handle_async_request
    )
    return fake


def _client(configured: ScriptedChatModel) -> TestClient:
    """The greeter agent on configured, served over A2A"""
    app = FastAPI()
    add_executable_routes(
        app,
        [
            Executable(
                kind="agent",
                name="greeter",
                description="Greets whoever writes to it",
                graph=build_agent(Agent.load(GREETER), model=configured),
            )
        ],
        InMemoryTaskStore(),
        AppSettings(),
    )
    return TestClient(app)


def _rpc(client: TestClient, method: str, params: dict[str, JsonValue]) -> str:
    """The raw JSON-RPC response to one call"""
    return client.post(
        PATH,
        headers={"A2A-Version": "1.0"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    ).text


def _say(client: TestClient, metadata: dict[str, JsonValue] | None) -> str:
    """Sends hi with metadata and returns the raw SendMessage response"""
    message = {"messageId": "m-1", "role": "ROLE_USER", "parts": [{"text": "hi"}]}
    return _rpc(
        client,
        "SendMessage",
        {"message": message, **({"metadata": metadata} if metadata else {})},
    )


def _task(response: str) -> dict[str, JsonValue]:
    """The task a SendMessage response carries"""
    return json.loads(response)["result"]["task"]


def test_a_run_calls_the_model_the_metadata_names_on_the_servers_key(
    anthropic: FakeAnthropic,
):
    configured = ScriptedChatModel(replies=[AIMessage("Hello from glm")])

    task = _task(_say(_client(configured), METADATA))

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello from Claude"
    [request] = anthropic.requests
    assert request.headers["authorization"] == f"Bearer {SERVER_KEY}"
    assert json.loads(request.content)["model"] == "claude-sonnet-5-5"
    assert json.loads(request.content)["thinking"] == {
        "type": "adaptive",
        "display": "summarized",
    }
    assert json.loads(request.content)["output_config"] == {"effort": "low"}
    assert configured.requests == []


def test_without_metadata_a_run_keeps_its_configured_model(anthropic: FakeAnthropic):
    configured = ScriptedChatModel(replies=[AIMessage("Hello from glm")])

    task = _task(_say(_client(configured), None))

    [reply] = [a for a in task["artifacts"] if a["name"] == "greeter"]
    assert reply["parts"][0]["text"] == "Hello from glm"
    assert anthropic.requests == []


def test_a_model_the_harness_does_not_offer_fails_the_task(anthropic: FakeAnthropic):
    metadata = {"model": {"family": "claude", "model": "claude-9"}}

    task = _task(_say(_client(ScriptedChatModel(replies=[])), metadata))

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"][0]["text"] == (
        "ezcareer-harness does not offer claude-9 for claude"
    )
    assert anthropic.requests == []


def test_invalid_metadata_fails_the_task(anthropic: FakeAnthropic):
    task = _task(_say(_client(ScriptedChatModel(replies=[])), {"model": "claude"}))

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"][0]["text"].startswith("Invalid input:")
    assert anthropic.requests == []
