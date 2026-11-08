from functools import partial

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from pydantic import JsonValue

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant.test_career_consultant import (
    GOOD_EDIT,
    _answer,
    _model,
)
from tests.agents.test_builder import _call
from tests.features.write_document.test_validate_changeset import BAD_EDIT
from tests.features.write_document.test_write_document_graph import _input, _print


def _client(*replies: AIMessage) -> TestClient:
    container = Container()
    container.artifact_service_http_client(
        transport=httpx.MockTransport(partial(_print, sent=[]))
    )
    container.career_consultant(model=_model(*replies))
    return TestClient(create_app(container))


def _send(
    client: TestClient, data: JsonValue, task: dict[str, JsonValue] | None = None
) -> dict[str, JsonValue]:
    message = {
        "messageId": f"m-{id(data)}",
        "role": "ROLE_USER",
        "parts": [{"data": data}],
    }
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


def test_an_edit_request_returns_the_checked_changeset():
    task = _send(_client(_answer(GOOD_EDIT)), _input().model_dump(mode="json"))

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [artifact] = task["artifacts"]
    changeset = artifact["parts"][0]["data"]["changeset"]
    assert changeset["agent"] == "career-consultant"
    assert changeset["status"] == "pending"
    assert changeset["edits"] == [GOOD_EDIT.model_dump(mode="json")]


def test_an_unclear_request_shows_the_user_a_widget_then_finishes():
    client = _client(_call("clarify", question="Which job?"), _answer(GOOD_EDIT))

    asked = _send(client, _input().model_dump(mode="json"))
    done = _send(client, {"input": "Lumen Pay"}, task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which job?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"


def test_a_changeset_that_never_passes_fails_without_one():
    task = _send(_client(_answer(BAD_EDIT)), _input().model_dump(mode="json"))

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert "artifacts" not in task
