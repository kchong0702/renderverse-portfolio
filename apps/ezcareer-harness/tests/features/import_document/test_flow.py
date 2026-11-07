from base64 import b64encode

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.a2a import Executable, add_executable_routes
from src.app.container import Container
from src.core.config import AppSettings, reload_settings
from src.features.import_document import (
    ImportInput,
    ImportResult,
    build_task_graph,
    run_import,
)
from src.shared.extraction import Line
from tests.fakes import artifact_service, replying
from tests.features.import_document.test_import import PDF, answer


def test_an_unreadable_upload_fails_the_task_with_its_reason(monkeypatch):
    monkeypatch.setenv("AIGW_UPSTREAM_URL", "http://gateway.test/v1")
    monkeypatch.setenv("AIGW_PASSTHROUGH_KEY", "test-key")
    reload_settings()
    app = FastAPI()
    add_executable_routes(app, Container().executables(), AppSettings())
    message = {
        "messageId": "m-1",
        "role": "ROLE_USER",
        "parts": [{"data": {"file": b64encode(b"%PDF-1.7 broken").decode()}}],
    }

    response = TestClient(app).post(
        "/ezcareer/a2a/import-resume",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )

    task = response.json()["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert (
        task["status"]["message"]["parts"][0]["text"]
        == "the file is not a readable PDF"
    )


def test_the_result_carries_its_pdf_as_base64():
    result = ImportResult.model_validate(
        {
            "document": {
                "kind": "resume",
                "content": {
                    "blocks": [
                        {"kind": "profile", "id": "profile", "name": {"text": "Ada"}}
                    ]
                },
            },
            "pdf": b"%PDF-\xff",
            "report": {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.5},
            "lines": [
                Line(id="p1.s1", text="Ada", page=1, x0=0, top=0, x1=1, bottom=1)
            ],
            "rounds": [[]],
            "config_hash": "abc",
        }
    )

    assert result.model_dump(mode="json")["pdf"] == b64encode(b"%PDF-\xff").decode()


def test_a_completed_import_returns_its_result_as_the_artifact(config):
    app = FastAPI()
    graph = build_task_graph(
        lambda file: run_import(
            file, config, artifact_service([]), replying(answer("Engineer"))
        )
    )
    executable = Executable(
        name="import-resume",
        description="Import",
        input_schema=ImportInput,
        graph=graph,
    )
    add_executable_routes(app, [executable], AppSettings())
    message = {
        "messageId": "m-2",
        "role": "ROLE_USER",
        "parts": [{"data": {"file": b64encode(PDF).decode()}}],
    }

    response = TestClient(app).post(
        "/ezcareer/a2a/import-resume",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )

    task = response.json()["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [part] = task["artifacts"][0]["parts"]
    result = part["data"]["result"]
    assert result["pdf"] == b64encode(b"%PDF-fake").decode()
    assert [line["id"] for line in result["lines"]] == ["p1.s1", "p1.s2"]
    assert "file" not in part["data"]
