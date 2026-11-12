from base64 import b64decode
from datetime import timedelta
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select

from src.db.base import utcnow
from src.db.queue import claim, complete, fail, heartbeat
from src.features.connections import Connection
from src.features.imports.models import Import
from src.features.imports.processing import IMPORTS, process_import
from tests.conftest import PREFIX, a2a_sent, a2a_task, work

DOCUMENTS = f"{PREFIX}/documents"

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

SUGGESTION = {"template": "serif", "columns": 1, "traits": ["serif_font"]}

PDF = b"%PDF-1.7 resume \xfb\xff"


async def _upload(client, path: str = f"{DOCUMENTS}/imports", content: bytes = PDF):
    """Upload a résumé to Documents, or to the path given, and return the import"""
    uploaded = await client.post(
        path, files={"file": ("kelvin-chong-resume.pdf", content, "application/pdf")}
    )
    assert uploaded.status_code == 201
    return uploaded.json()


async def _listed(client, import_id: str) -> dict:
    """The import with this id, from the profile's imports list"""
    return next(
        row
        for row in (await client.get(f"{PREFIX}/profile/imports")).json()
        if row["id"] == import_id
    )


async def _import(app, client, harness, outcome) -> dict:
    """Upload a résumé to Documents and work the queue with import-resume answering
    outcome; the import as it ends up"""
    uploaded = await _upload(client)
    harness.outcomes = [outcome]
    await work(app)
    return await _listed(client, uploaded["id"])


def _imported(document: dict = IMPORTED) -> dict:
    """import-resume's reply for the upload"""
    reply = {
        "document": document,
        "pdf": "JVBERi0=",
        "report": {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.4},
        "lines": LINES,
        "suggestion": SUGGESTION,
    }
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply}])


async def _due(app, import_id: str) -> None:
    """Let the import be claimed now, as if its backoff had passed"""
    async with app.state.session_factory() as session, session.begin():
        row = await session.get(Import, UUID(import_id))
        row.run_after = utcnow() - timedelta(seconds=1)


async def test_a_worker_turns_an_upload_into_its_draft(app, client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()

    done = await _import(app, client, harness, _imported())

    assert done["status"] == "done"
    assert done["error"] == ""
    assert done["finished_at"] is not None
    assert done["suggestion"] == SUGGESTION
    assert (await client.get(f"{PREFIX}/imports/active")).json() == []
    document = (await client.get(f"{DOCUMENTS}/{done['document_id']}")).json()
    assert document["lines"] == [{"id": "p1.s1", "text": "Kelvin Chong"}]
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


async def test_an_import_syncs_the_profile_and_the_same_file_again_adds_nothing(
    app, client, harness
):
    done = await _import(app, client, harness, _imported())

    assert (await client.get(f"{PREFIX}/profile")).json()["name"] == "Kelvin Chong"
    assert (done["source"], done["filename"], done["added"]) == (
        "documents",
        "kelvin-chong-resume.pdf",
        1,
    )
    again = await _upload(client, f"{PREFIX}/profile/imports")
    harness.outcomes = [_imported()]
    await work(app)
    again = await _listed(client, again["id"])
    assert (again["source"], again["status"], again["added"]) == ("data", "done", 0)
    assert len(harness.received) == 2
    assert (await client.get(DOCUMENTS)).json()[0]["title"] == "kelvin-chong-resume"
    assert len((await client.get(DOCUMENTS)).json()) == 1


async def test_an_import_keeps_the_blocks_its_design_places(app, client, harness):
    layouts = [{"template": "serif", "region": "top", "blocks": ["profile"]}]
    design = {"template": "serif", "layouts": layouts}

    done = await _import(
        app, client, harness, _imported({**IMPORTED, "design": design})
    )

    assert done["status"] == "done"
    document = (await client.get(f"{DOCUMENTS}/{done['document_id']}")).json()
    assert document["body"]["design"]["layouts"] == layouts


async def test_a_file_the_harness_cannot_read_fails_at_once_with_the_reason(
    app, client, harness
):
    reason = "The file has no text to read"

    failed = await _import(
        app, client, harness, a2a_task("FAILED", status_parts=[{"text": reason}])
    )

    assert failed["status"] == "failed"
    assert failed["error"] == reason
    assert failed["finished_at"] is not None
    assert failed["document_id"] is None
    assert (await client.get(DOCUMENTS)).json() == []
    assert (await client.get(f"{PREFIX}/imports/active")).json() == []
    harness.outcomes = [_imported()]
    await _due(app, failed["id"])
    await work(app)
    assert len(harness.received) == 1


async def test_the_same_bytes_under_a_new_name_are_imported_under_that_name(
    app, client, harness
):
    await _import(app, client, harness, _imported())
    harness.outcomes = [_imported()]

    renamed = await client.post(
        f"{DOCUMENTS}/imports", files={"file": ("cv-2026.pdf", PDF, "application/pdf")}
    )
    await work(app)

    assert renamed.status_code == 201
    assert (await _listed(client, renamed.json()["id"]))["filename"] == "cv-2026.pdf"
    assert [d["title"] for d in (await client.get(DOCUMENTS)).json()] == [
        "cv-2026",
        "kelvin-chong-resume",
    ]


async def test_a_done_import_is_not_processed_twice(app, client, harness):
    done = await _import(app, client, harness, _imported())
    harness.outcomes = [_imported()]

    await work(app)

    assert len(harness.received) == 1
    assert (await _listed(client, done["id"]))["status"] == "done"


async def test_an_unreadable_jsearch_key_fails_the_import_at_once(app, client, harness):
    await client.put(
        f"{PREFIX}/settings/connections/jsearch", json={"api_key": "rapidapi-key"}
    )
    async with app.state.session_factory() as session, session.begin():
        stored = await session.scalar(select(Connection))
        stored.secret = Fernet(Fernet.generate_key()).encrypt(b"other")

    failed = await _import(app, client, harness, _imported())

    assert failed["status"] == "failed"
    assert "change it in Settings" in failed["error"]
    assert failed["finished_at"] is not None
    assert harness.received == []
    assert (await client.get(f"{PREFIX}/imports/active")).json() == []


async def test_an_unreachable_harness_queues_the_import_again(app, client, harness):
    harness.down = True

    queued = await _import(app, client, harness, _imported())

    assert queued["status"] == "queued"
    assert queued["error"] != ""
    assert (await client.get(f"{PREFIX}/imports/active")).json()[0]["id"] == queued[
        "id"
    ]
    harness.down = False
    harness.outcomes = [_imported()]
    await work(app)
    assert len(harness.received) == 0
    await _due(app, queued["id"])
    await work(app)
    done = await _listed(client, queued["id"])
    assert (done["status"], done["error"]) == ("done", "")


async def test_a_heartbeat_after_the_import_ended_under_its_claim_still_holds(
    app, client, harness
):
    first = await _upload(client)
    async with app.state.session_factory() as session, session.begin():
        claimed = await claim(session, IMPORTS, timedelta(seconds=60))
        await complete(session, IMPORTS, claimed.id, claimed.claim_token)
    second = await _upload(client, f"{PREFIX}/profile/imports")
    async with app.state.session_factory() as session, session.begin():
        retried = await claim(session, IMPORTS, timedelta(seconds=60))
        await fail(
            session, IMPORTS, retried.id, retried.claim_token, "away", retry=True
        )

    async with app.state.session_factory() as session, session.begin():
        after_done = await heartbeat(
            session, IMPORTS, claimed.id, claimed.claim_token, timedelta(seconds=60)
        )
        after_retry = await heartbeat(
            session, IMPORTS, retried.id, retried.claim_token, timedelta(seconds=60)
        )

    assert (claimed.id, retried.id) == (UUID(first["id"]), UUID(second["id"]))
    assert (after_done, after_retry) == (True, True)


async def test_an_import_carries_the_users_model(app, client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})

    await _import(app, client, harness, _imported())

    assert [sent["params"]["metadata"] for sent in a2a_sent(harness)] == [
        {"model": model}
    ]


async def test_an_import_past_the_documents_limit_fails_and_writes_nothing(
    app, client, harness
):
    for number in range(10):
        await client.post(
            DOCUMENTS, json={"title": f"Résumé {number}", "body": IMPORTED}
        )

    failed = await _import(app, client, harness, _imported())

    assert failed["status"] == "failed"
    assert failed["error"] == (
        "You already keep 10 resume documents. Delete one to add another."
    )
    assert failed["document_id"] is None
    assert len((await client.get(DOCUMENTS)).json()) == 10
    assert (await client.get(f"{PREFIX}/profile")).json()["name"] == ""


async def test_a_new_upload_abandons_the_import_still_queued(client):
    first = await _upload(client)

    second = await _upload(client)

    listed = {i["id"]: i for i in (await client.get(f"{DOCUMENTS}/imports")).json()}
    assert listed[first["id"]]["status"] == "abandoned"
    assert listed[first["id"]]["finished_at"] is not None
    assert listed[second["id"]]["status"] == "queued"
    assert [i["id"] for i in (await client.get(f"{PREFIX}/imports/active")).json()] == [
        second["id"]
    ]


async def test_a_lost_claim_cannot_extend_or_complete_its_import(app, client, harness):
    first = await _upload(client)
    async with app.state.session_factory() as session, session.begin():
        claimed = await claim(session, IMPORTS, timedelta(seconds=60))
    assert claimed.id == UUID(first["id"])
    await _upload(client)
    harness.outcomes = [_imported()]

    async with app.state.session_factory() as session, session.begin():
        extended = await heartbeat(
            session, IMPORTS, claimed.id, claimed.claim_token, timedelta(seconds=60)
        )
        completed = await complete(session, IMPORTS, claimed.id, claimed.claim_token)
    await process_import(claimed.id, claimed.claim_token, app.state.container)

    assert (extended, completed) == (False, None)
    assert harness.received == []
    assert (await _listed(client, first["id"]))["status"] == "abandoned"
    assert (await client.get(DOCUMENTS)).json() == []


async def test_active_imports_list_both_sources_oldest_first(client):
    documents = await _upload(client)
    data = await _upload(client, f"{PREFIX}/profile/imports")

    active = (await client.get(f"{PREFIX}/imports/active")).json()

    assert [(i["id"], i["source"]) for i in active] == [
        (documents["id"], "documents"),
        (data["id"], "data"),
    ]
    assert [i["id"] for i in (await client.get(f"{DOCUMENTS}/imports")).json()] == [
        documents["id"]
    ]
    assert [
        i["id"] for i in (await client.get(f"{PREFIX}/profile/imports")).json()
    ] == [
        data["id"],
        documents["id"],
    ]


async def test_a_finished_import_stays_in_the_history(app, client, harness):
    done = await _import(app, client, harness, _imported())

    removed = await client.delete(f"{DOCUMENTS}/imports/{done['id']}")

    assert removed.status_code == 409
    assert [i["id"] for i in (await client.get(f"{DOCUMENTS}/imports")).json()] == [
        done["id"]
    ]
    document = (await client.get(f"{DOCUMENTS}/{done['document_id']}")).json()
    assert document["lines"] == [{"id": "p1.s1", "text": "Kelvin Chong"}]
    missing = await client.delete(f"{DOCUMENTS}/imports/{uuid4()}")
    assert missing.status_code == 404
