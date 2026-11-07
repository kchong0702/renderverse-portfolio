import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from document_schema import AnyDocument
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import TypeAdapter

from src.app.a2a import Flow, add_flow_routes
from src.core.config import AppSettings
from src.core.errors import FlowError
from src.features import write_document
from src.shared.clients.artifact_service import ArtifactService
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_career_consultant import (
    BAD_EDIT,
    GOOD_EDIT,
    _call,
    _changeset,
)
from tests.features.write_document.test_edit_graph import _render

FIXTURES = Path(__file__).parents[1] / "features/write_document/fixtures"
PATH = "/ezcareer/a2a/edit-document"
REPORT = {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.5}


def _client(*replies: AIMessage) -> TestClient:
    model = ScriptedChatModel(replies=list(replies))
    graph = write_document.edit_graph(_render, InMemorySaver(), model)
    app = FastAPI()
    flow = Flow(
        name="edit-document",
        description="Edits",
        input_schema=write_document.EditInput,
        graph=graph,
    )
    add_flow_routes(app, [flow], AppSettings())
    return TestClient(app)


def _request() -> dict[str, Any]:
    return {
        "request": "Mention my Kubernetes work",
        "document": json.loads((FIXTURES / "resume.json").read_text()),
        "report": REPORT,
        "lines": [
            {**line, "page": 1, "x0": 0, "top": 0, "x1": 1, "bottom": 1}
            for line in json.loads((FIXTURES / "lines.json").read_text())
        ],
        "facts": json.loads((FIXTURES / "facts.json").read_text()),
    }


def _send(client: TestClient, data: object, task: dict | None = None) -> dict:
    message = {
        "messageId": f"m-{id(data)}",
        "role": "ROLE_USER",
        "parts": [{"data": data}],
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


def test_an_edit_request_returns_the_checked_changeset():
    task = _send(_client(_call("Changeset", **_changeset(GOOD_EDIT))), _request())

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [artifact] = task["artifacts"]
    changeset = artifact["parts"][0]["data"]["changeset"]
    assert changeset["agent"] == "career-consultant"
    assert changeset["status"] == "pending"
    assert [edit["path"] for edit in changeset["edits"]] == [GOOD_EDIT["path"]]


def test_an_unclear_request_asks_the_user_then_finishes():
    client = _client(
        _call("ask_user", question="Which job?"),
        _call("Changeset", **_changeset(GOOD_EDIT)),
    )

    asked = _send(client, _request())
    done = _send(client, "Lumen Pay", task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == "Which job?"
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"


def test_a_changeset_that_never_passes_fails_without_one():
    task = _send(_client(_call("Changeset", **_changeset(BAD_EDIT))), _request())

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert "artifacts" not in task


async def test_render_prints_with_the_documents_template_spec():
    document = TypeAdapter(AnyDocument).validate_python(
        json.loads((FIXTURES / "resume.json").read_text())
    )
    sent: list[dict[str, Any]] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"pdf": "JVBERg==", "report": REPORT})

    render = write_document.render_with(
        ArtifactService(
            httpx.AsyncClient(
                transport=httpx.MockTransport(answer), base_url="http://a"
            )
        ),
        FIXTURES / "templates",
    )

    report = await render(document, {"a" * 64: b"photo"})

    assert report.pages == 1
    assert sent[0]["template"]["id"] == "classic"
    assert sent[0]["assets"] == {"a" * 64: "cGhvdG8="}


async def test_a_failed_print_fails_the_edit_with_a_reason():
    document = TypeAdapter(AnyDocument).validate_python(
        json.loads((FIXTURES / "resume.json").read_text())
    )
    render = write_document.render_with(
        ArtifactService(
            httpx.AsyncClient(
                transport=httpx.MockTransport(lambda request: httpx.Response(500)),
                base_url="http://a",
            )
        ),
        FIXTURES / "templates",
    )

    with pytest.raises(FlowError, match="Couldn't print"):
        await render(document, {})
