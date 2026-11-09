from functools import partial

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant.test_career_consultant import (
    GOOD_EDIT,
    _answer,
    _model,
)
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_validate_changeset import BAD_EDIT
from tests.features.write_document.test_write_document_graph import _input, _print


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


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    response = client.post(
        "/ezcareer/a2a/edit-document",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )
    return response.json()["result"]["task"]


def _request() -> list[dict[str, JsonValue]]:
    return [
        {"text": "Mention my Kubernetes work"},
        {"data": _input().model_dump(mode="json", exclude={"messages"})},
    ]


def test_an_edit_request_returns_the_checked_changeset():
    model = _model(_answer(GOOD_EDIT))

    task = _send(_client(model), _request())

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [artifact] = task["artifacts"]
    changeset = artifact["parts"][0]["data"]["changeset"]
    assert changeset["agent"] == "career-consultant"
    assert changeset["status"] == "pending"
    assert changeset["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    assert model.requests[0][1].text.endswith(
        "The user asks: Mention my Kubernetes work"
    )


def test_an_unclear_request_shows_the_user_a_widget_then_finishes():
    client = _client(
        _model(_call("clarify", question="Which job?"), _answer(GOOD_EDIT))
    )

    asked = _send(client, _request())
    done = _send(client, [{"data": {"input": "Lumen Pay"}}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which job?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"


def test_a_changeset_that_never_passes_fails_without_one():
    task = _send(_client(_model(_answer(BAD_EDIT))), _request())

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert "artifacts" not in task
