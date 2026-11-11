from base64 import b64encode
from functools import partial

from fastapi.testclient import TestClient
from pydantic import JsonValue

from src.app.app import create_app
from src.app.container import Container
from src.features.import_document import build_graph
from tests.conftest import ScriptedChatModel
from tests.features.import_document.test_extract import _artifact_service
from tests.features.import_document.test_import_graph import _model, _reply
from tests.features.write_document.test_write_document_graph import _print
from tests.pdfs import make_pdf

PDF = make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])


def _client(model: ScriptedChatModel) -> TestClient:
    """The app with import-resume on model, converting and printing through a fake
    artifact-service"""
    container = Container()
    container.import_document.import_resume_executable(
        graph=build_graph(
            container.import_document.agent(model=model),
            _artifact_service(partial(_print, sent=[])),
            checkpointer=container.checkpointer(),
        )
    )
    return TestClient(create_app(container))


def _send(
    client: TestClient, parts: list[dict[str, JsonValue]]
) -> dict[str, JsonValue]:
    """Sends parts to import-resume over A2A and returns the task"""
    response = client.post(
        "/ezcareer/a2a/import-resume",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {"messageId": "m-1", "role": "ROLE_USER", "parts": parts}
            },
        },
    )
    return response.json()["result"]["task"]


def test_an_unreadable_upload_fails_the_task_with_its_reason():
    task = _send(
        _client(_model()),
        [{"data": {"file": b64encode(b"%PDF-1.7 broken").decode()}}],
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert (
        task["status"]["message"]["parts"][0]["text"]
        == "the file is not a readable PDF"
    )


def test_a_completed_import_returns_its_result_as_the_artifact():
    model = _model(_reply("Engineer"))

    task = _send(
        _client(model),
        [
            {"text": "Keep my headline"},
            {"data": {"file": b64encode(PDF).decode()}},
        ],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [part] = task["artifacts"][0]["parts"]
    assert sorted(part["data"]) == ["document", "lines", "pdf", "report", "suggestion"]
    assert part["data"]["suggestion"] == {
        "template": "classic",
        "columns": 1,
        "traits": [],
    }
    assert part["data"]["pdf"] == "JVBERg=="
    assert [line["id"] for line in part["data"]["lines"]] == ["p1.s1", "p1.s2"]
    assert model.requests[0][-1].text == "Keep my headline"
