from base64 import b64encode

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.a2a import FLOWS, add_flow_routes
from src.core.config import AppSettings
from src.features.import_document import ImportResult
from src.shared.extraction import Line


def test_an_unreadable_upload_fails_the_task_with_its_reason():
    app = FastAPI()
    add_flow_routes(app, FLOWS, AppSettings())
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
