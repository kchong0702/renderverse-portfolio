import json
from functools import partial

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from pydantic import JsonValue

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant.test_career_consultant import (
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    READ_SKILL,
    _model,
    _propose,
)
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_write_document_graph import (
    _input,
    _loaded,
    _print,
)


def _client(model: ScriptedChatModel) -> TestClient:
    container = Container()
    container.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    container.career_consultant.agent(model=model)
    return TestClient(create_app(container))


def _message(
    parts: list[dict[str, JsonValue]], task: dict[str, JsonValue] | None
) -> dict[str, JsonValue]:
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    return message


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    response = client.post(
        "/ezcareer/a2a/edit-document",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": _message(parts, task)},
        },
    )
    return response.json()["result"]["task"]


def _stream(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue],
) -> list[dict[str, JsonValue]]:
    """Every event SendStreamingMessage sends for one message"""
    with client.stream(
        "POST",
        "/ezcareer/a2a/edit-document",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendStreamingMessage",
            "params": {"message": _message(parts, task)},
        },
    ) as response:
        return [
            json.loads(line.removeprefix("data: "))["result"]
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]


def _request() -> list[dict[str, JsonValue]]:
    return [
        {"text": "Mention my Kubernetes work"},
        {"data": _input().model_dump(mode="json", exclude={"messages"})},
    ]


def test_a_message_loads_the_document_then_returns_the_reply_and_changeset():
    model = _model(READ_SKILL, _propose(GOOD_EDIT), DONE)
    client = _client(model)

    asked = _send(client, _request())
    done = _send(client, [{"data": _loaded()}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"] == [
        {"data": {"execute_tool": "document", "id": "doc-1"}}
    ]
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [artifact] = [a for a in done["artifacts"] if a["name"] == "edit-document"]
    output = artifact["parts"][0]["data"]
    assert output["reply"] == DONE.text
    assert output["changeset"]["agent"] == "career-consultant"
    assert output["changeset"]["status"] == "pending"
    assert output["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    assert "<document>" in model.requests[0][0].text
    assert model.requests[0][1].text == "Mention my Kubernetes work"


def test_a_tool_ops_cannot_execute_fails_the_task_with_its_reason():
    client = _client(_model(DONE))

    asked = _send(client, _request())
    failed = _send(client, [{"data": {"error": "No document doc-1"}}], task=asked)

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"] == [{"text": "No document doc-1"}]
    assert "artifacts" not in failed


def test_an_unclear_request_shows_the_user_a_widget_then_finishes():
    client = _client(
        _model(
            _call("clarify", question="Which job?"),
            READ_SKILL,
            _propose(GOOD_EDIT),
            DONE,
        )
    )

    loading = _send(client, _request())
    asked = _send(client, [{"data": _loaded()}], task=loading)
    done = _send(client, [{"data": {"input": "Lumen Pay"}}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which job?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"


def test_an_agent_that_never_stops_proposing_fails_without_a_changeset():
    client = _client(_model(READ_SKILL, _propose(BAD_EDIT)))

    asked = _send(client, _request())
    task = _send(client, [{"data": _loaded()}], task=asked)

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert "artifacts" not in task


def test_the_consultants_thinking_and_reply_stream_before_the_output():
    client = _client(
        _model(
            AIMessage(
                [
                    {"type": "reasoning", "reasoning": "The summary names Kubernetes."},
                    {"type": "text", "text": "It already leads with Kubernetes."},
                ]
            )
        )
    )

    asked = _send(client, _request())
    events = _stream(client, [{"data": _loaded()}], asked)

    assert [
        (
            e["artifactUpdate"]["artifact"]["name"],
            e["artifactUpdate"]["artifact"]["parts"][0],
        )
        for e in events
        if "artifactUpdate" in e
    ] == [
        ("thinking", {"text": "The summary names Kubernetes."}),
        ("text", {"text": "It already leads with Kubernetes."}),
        (
            "edit-document",
            {
                "data": {
                    "reply": "It already leads with Kubernetes.",
                    "changeset": None,
                }
            },
        ),
    ]
    assert events[-1]["statusUpdate"]["status"]["state"] == "TASK_STATE_COMPLETED"
