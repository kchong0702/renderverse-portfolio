from base64 import b64decode
from datetime import timedelta
from uuid import UUID

from src.db.base import utcnow
from src.features.documents.enums import ImportStatus
from src.features.documents.models import DocumentImport
from tests.conftest import PREFIX, a2a_sent, a2a_task

DOCUMENTS = f"{PREFIX}/documents"
REQUEST_ID = "4c1f8e2a-9b3d-4e6f-8a1c-2d3e4f5a6b7c"

LINES = [
    {
        "id": "p1.s1",
        "text": "Kelvin Chong",
        "page": 1,
        "x0": 72.0,
        "top": 60.5,
        "x1": 180.25,
        "bottom": 74.0,
    }
]

IMPORTED = {
    "kind": "resume",
    "content": {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": {"text": "Kelvin Chong", "src": ["p1.s1"]},
            }
        ]
    },
}

CHANGESET = {
    "id": "tailor-1",
    "agent": "career-consultant",
    "reason": "Match the Northwind Labs posting.",
    "edits": [
        {
            "kind": "update_field",
            "path": "blocks/profile/headline",
            "value": {"text": "Backend engineer", "src": ["fact:role-1"]},
        }
    ],
}

WIDGET = {
    "label": "Did you use Kafka at work?",
    "input_placeholder": "Where",
    "submit_btn": "Send",
}

PDF = b"%PDF-1.7 resume \xfb\xff"


async def _import(client, harness, outcome):
    """Upload a résumé and read it with import-resume answering outcome"""
    uploaded = await client.post(
        f"{DOCUMENTS}/imports",
        files={"file": ("kelvin-chong-resume.pdf", PDF, "application/pdf")},
    )
    harness.outcomes = [outcome]
    return await client.post(f"{DOCUMENTS}/imports/{uploaded.json()['id']}/read")


def _imported() -> dict:
    """import-resume's reply for the upload"""
    reply = {
        "document": IMPORTED,
        "pdf": "JVBERi0=",
        "report": {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.4},
        "lines": LINES,
    }
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply}])


async def test_reading_an_import_makes_its_draft(client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()

    read = await _import(client, harness, _imported())

    assert read.status_code == 200
    assert read.json()["status"] == "done"
    assert read.json()["error"] == ""
    document = (await client.get(f"{DOCUMENTS}/{read.json()['document_id']}")).json()
    assert document["title"] == "kelvin-chong-resume"
    assert document["kind"] == "resume"
    assert document["body"]["content"]["blocks"][0]["name"]["src"] == ["p1.s1"]
    versions = (await client.get(f"{DOCUMENTS}/{document['id']}/versions")).json()
    assert [v["label"] for v in versions] == ["Imported"]
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/import-resume"
    message = a2a_sent(harness)[0]["params"]["message"]
    assert message["contextId"].startswith(f"{me['id']}:")
    [part] = message["parts"]
    assert b64decode(part["data"]["file"], validate=True) == PDF


async def test_a_failed_import_keeps_the_reason_and_can_be_read_again(client, harness):
    reason = "The file has no text to read"

    failed = await _import(
        client, harness, a2a_task("FAILED", status_parts=[{"text": reason}])
    )

    assert failed.json()["status"] == "failed"
    assert failed.json()["error"] == reason
    assert failed.json()["document_id"] is None
    assert (await client.get(DOCUMENTS)).json() == []
    harness.outcomes = [_imported()]
    again = await client.post(f"{DOCUMENTS}/imports/{failed.json()['id']}/read")
    assert again.json()["status"] == "done"
    assert again.json()["error"] == ""


async def test_a_done_import_is_not_read_twice(client, harness):
    read = await _import(client, harness, _imported())

    again = await client.post(f"{DOCUMENTS}/imports/{read.json()['id']}/read")

    assert again.status_code == 409
    assert len(harness.received) == 1


async def test_an_unreachable_harness_leaves_the_import_pending(client, harness):
    harness.down = True

    read = await _import(client, harness, _imported())

    assert read.status_code == 503
    assert [i["status"] for i in (await client.get(f"{DOCUMENTS}/imports")).json()] == [
        "pending"
    ]


async def _claimed_upload(app, client, claimed_ago: timedelta) -> str:
    """Upload a résumé whose read another request claimed claimed_ago"""
    uploaded = await client.post(
        f"{DOCUMENTS}/imports",
        files={"file": ("kelvin-chong-resume.pdf", PDF, "application/pdf")},
    )
    async with app.state.session_factory() as session:
        row = await session.get(DocumentImport, UUID(uploaded.json()["id"]))
        row.status = ImportStatus.RUNNING
        await session.flush()
        row.updated_at = utcnow() - claimed_ago
        await session.commit()
    return uploaded.json()["id"]


async def test_an_import_being_read_is_not_read_again(app, client, harness):
    import_id = await _claimed_upload(app, client, timedelta(seconds=1))
    harness.outcomes = [_imported()]

    again = await client.post(f"{DOCUMENTS}/imports/{import_id}/read")

    assert again.status_code == 409
    assert harness.received == []


async def test_a_read_that_outlived_the_run_timeout_can_be_claimed_again(
    app, client, harness
):
    import_id = await _claimed_upload(app, client, timedelta(hours=1))
    harness.outcomes = [_imported()]

    read = await client.post(f"{DOCUMENTS}/imports/{import_id}/read")

    assert read.status_code == 200
    assert read.json()["status"] == "done"


async def test_an_edit_request_stores_the_changeset_for_review(client, harness):
    read = await _import(client, harness, _imported())
    document_id = read.json()["document_id"]
    facts = (await client.get(f"{PREFIX}/profile/agent")).json()["facts"]
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"changeset": CHANGESET}}])
    ]
    document = (await client.get(f"{DOCUMENTS}/{document_id}")).json()

    response = await client.post(
        f"{DOCUMENTS}/{document_id}/edit-requests/{REQUEST_ID}",
        json={"text": "Tailor it for Northwind Labs"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["reply"]["changeset"]["status"] == "pending"
    listed = (await client.get(f"{DOCUMENTS}/{document_id}/changesets")).json()
    assert [c["id"] for c in listed] == [response.json()["reply"]["id"]]
    assert (await client.get(DOCUMENTS)).json()[0]["pending_changesets"] == 1
    edit = a2a_sent(harness)[1]["params"]["message"]
    assert harness.received[1].url.path == "/ezcareer/a2a/edit-document"
    assert edit["contextId"] == f"{me['id']}:{REQUEST_ID}"
    assert edit["parts"] == [
        {"text": "Tailor it for Northwind Labs"},
        {"data": {"document": document["body"], "lines": LINES, "facts": facts}},
    ]


async def test_an_edit_request_asks_back_and_the_answer_resumes_it(client, harness):
    document = (
        await client.post(DOCUMENTS, json={"title": "Résumé", "body": IMPORTED})
    ).json()
    url = f"{DOCUMENTS}/{document['id']}/edit-requests/{REQUEST_ID}"
    harness.outcomes = [
        a2a_task("INPUT_REQUIRED", status_parts=[{"data": WIDGET}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"changeset": CHANGESET}}]),
    ]

    asked = await client.post(url, json={"text": "Add Kafka"})
    done = await client.post(f"{url}/tasks/task-1/answer", json={"input": "Acme"})

    assert asked.json() == {
        "status": "input_required",
        "task_id": "task-1",
        "widget": {
            "label": WIDGET["label"],
            "input_value": None,
            "input_placeholder": "Where",
            "submit_btn": "Send",
            "cancel_btn": None,
            "choose": None,
            "kind": None,
        },
    }
    assert done.json()["status"] == "completed"
    assert done.json()["reply"]["changeset"]["id"] == "tailor-1"
    first, resume = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert first["parts"][1]["data"]["lines"] == []
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == first["contextId"]
    assert resume["parts"] == [{"data": {"input": "Acme", "accept": None}}]


async def test_each_run_carries_the_users_model(client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})
    read = await _import(client, harness, _imported())
    url = f"{DOCUMENTS}/{read.json()['document_id']}/edit-requests/{REQUEST_ID}"
    harness.outcomes = [
        a2a_task("INPUT_REQUIRED", status_parts=[{"data": WIDGET}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"changeset": CHANGESET}}]),
    ]

    await client.post(url, json={"text": "Add Kafka"})
    await client.post(f"{url}/tasks/task-1/answer", json={"input": "Acme"})

    assert [sent["params"]["metadata"] for sent in a2a_sent(harness)] == [
        {"model": model}
    ] * 3


async def test_a_failed_edit_request_returns_its_reason(client, harness):
    document = (
        await client.post(DOCUMENTS, json={"title": "Résumé", "body": IMPORTED})
    ).json()
    reason = "Ran out of steps before finishing"
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": reason}])]

    response = await client.post(
        f"{DOCUMENTS}/{document['id']}/edit-requests/{REQUEST_ID}",
        json={"text": "Shorten it"},
    )

    assert response.json() == {"status": "failed", "reason": reason}
    assert (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json() == []
