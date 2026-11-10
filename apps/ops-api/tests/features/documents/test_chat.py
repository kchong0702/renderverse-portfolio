from uuid import UUID

from src.core.auth.models import User
from src.features.documents.models import Document
from tests.conftest import (
    PREFIX,
    a2a_sent,
    sse_events,
    sse_ids,
    stream_chunk,
    stream_status,
    stream_task,
)

DOCUMENTS = f"{PREFIX}/documents"

RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}},
            {"kind": "summary", "id": "sum", "text": {"html": "Backend engineer."}},
        ]
    },
}

TAILOR = {
    "id": "tailor-1",
    "agent": "career-consultant",
    "reason": "Match the Northwind Labs posting.",
    "edits": [
        {
            "kind": "update_field",
            "path": "blocks/sum/text",
            "value": {"html": "Backend engineer, 7 years.", "src": ["fact:role-1"]},
        }
    ],
}

WIDGET = {"label": "Which posting?", "input_placeholder": "Company"}


async def _document(client) -> dict:
    """Add the résumé the chat is about"""
    response = await client.post(
        DOCUMENTS, json={"title": "Master résumé", "body": RESUME}
    )
    return response.json()


def _fetches(document_id: str) -> list[dict]:
    """edit-document starting and pausing to fetch the document"""
    return [
        stream_task(),
        stream_status(
            "INPUT_REQUIRED", [{"data": {"fetch": "document", "id": document_id}}]
        ),
    ]


def _replies(reply: str, changeset: dict | None) -> list[dict]:
    """edit-document thinking, then replying with any changeset it proposes"""
    return [
        stream_chunk("thinking-1", "thinking", {"text": "Read the summary."}),
        stream_chunk(
            "a-1", "edit-document", {"data": {"reply": reply, "changeset": changeset}}
        ),
        stream_status("COMPLETED"),
    ]


async def test_a_chat_turn_stores_the_edits_it_proposes_before_its_reply(
    client, harness
):
    document = await _document(client)
    me = (await client.get(f"{PREFIX}/me")).json()
    facts = (await client.get(f"{PREFIX}/profile/agent")).json()["facts"]
    harness.outcomes = [
        _fetches(document["id"]),
        _replies("I added your years of experience.", TAILOR),
    ]

    response = await client.post(
        f"{DOCUMENTS}/{document['id']}/chat/messages", json={"text": "Mention my years"}
    )

    [stored] = (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json()
    assert stored["changeset"]["status"] == "pending"
    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "thinking", "turn": "thinking-1", "text": "Read the summary."},
        {
            "status": "changeset",
            "document_id": document["id"],
            "title": "Master résumé",
            "changeset_id": stored["id"],
            "edits": 1,
        },
        {"status": "completed", "reply": "I added your years of experience."},
    ]
    first, fetched = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert harness.received[0].url.path == "/ezcareer/a2a/edit-document"
    assert first["contextId"] == f"{me['id']}:document:{document['id']}"
    assert first["parts"] == [
        {"text": "Mention my years"},
        {"data": {"document_id": document["id"], "facts": facts}},
    ]
    assert fetched["taskId"] == "task-1"
    assert fetched["parts"] == [{"data": {"document": document["body"], "lines": []}}]


async def test_a_chat_turn_asks_back_and_the_answer_replies_without_edits(
    client, harness
):
    document = await _document(client)
    chat = f"{DOCUMENTS}/{document['id']}/chat"
    harness.outcomes = [
        _fetches(document["id"]),
        [stream_status("INPUT_REQUIRED", [{"data": WIDGET}])],
        _replies("Your summary already fits Northwind.", None),
    ]

    asked = await client.post(f"{chat}/messages", json={"text": "Tailor it"})
    done = await client.post(f"{chat}/tasks/task-1/answer", json={"input": "Northwind"})

    assert sse_events(asked)[-1]["status"] == "input_required"
    assert sse_events(done) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "thinking", "turn": "thinking-1", "text": "Read the summary."},
        {"status": "completed", "reply": "Your summary already fits Northwind."},
    ]
    assert (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json() == []
    resume = a2a_sent(harness)[-1]["params"]["message"]
    assert resume["parts"] == [{"data": {"input": "Northwind", "accept": None}}]


async def test_a_broken_chat_stream_resumes_after_the_last_event_it_got(
    client, harness
):
    document = await _document(client)
    chat = f"{DOCUMENTS}/{document['id']}/chat"
    harness.outcomes = [_fetches(document["id"]), _replies("Done.", TAILOR)]
    first = await client.post(f"{chat}/messages", json={"text": "Tighten it"})

    resumed = await client.get(
        f"{chat}/stream", headers={"Last-Event-ID": sse_ids(first)[1]}
    )

    assert sse_events(resumed) == sse_events(first)[2:]
    assert sse_ids(resumed) == sse_ids(first)[2:]


async def test_a_chat_takes_no_new_message_while_its_turn_runs(app, client, harness):
    document = await _document(client)
    me = (await client.get(f"{PREFIX}/me")).json()
    await app.state.container.store().create(
        UUID(me["id"]), f"{me['id']}:document:{document['id']}", "edit-document"
    )

    response = await client.post(
        f"{DOCUMENTS}/{document['id']}/chat/messages", json={"text": "Again"}
    )

    assert response.status_code == 409
    assert harness.received == []


async def test_another_users_document_has_no_chat(app, client, harness):
    mine = await _document(client)
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.flush()
        theirs = Document(
            user_id=other.id,
            kind="resume",
            title="Theirs",
            body=(await session.get(Document, UUID(mine["id"]))).body,
        )
        session.add(theirs)
        await session.commit()

    response = await client.post(
        f"{DOCUMENTS}/{theirs.id}/chat/messages", json={"text": "Tailor it"}
    )

    assert response.status_code == 404
    assert harness.received == []


async def test_stop_cancels_the_document_chats_running_task(client, harness):
    document = await _document(client)
    me = (await client.get(f"{PREFIX}/me")).json()
    task = {
        "id": "task-1",
        "contextId": f"{me['id']}:document:{document['id']}",
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}, {"result": task}]

    response = await client.post(
        f"{DOCUMENTS}/{document['id']}/chat/tasks/task-1/cancel"
    )

    assert response.status_code == 204
    assert [s["method"] for s in a2a_sent(harness)] == ["GetTask", "CancelTask"]
