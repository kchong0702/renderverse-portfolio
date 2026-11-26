import asyncio
from uuid import UUID

import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.core.auth.models import User
from src.features.conversations.models import AgentThread
from src.features.documents.models import Document
from tests.conftest import (
    PREFIX,
    a2a_accepted,
    a2a_sent,
    a2a_turn,
    ask,
    interrupt_part,
    sent_messages,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
    thread_of,
)
from tests.core.conftest import DATABASE_URL

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


async def _document(client) -> dict:
    """Add the résumé the editor chat is about"""
    response = await client.post(
        DOCUMENTS, json={"title": "Master résumé", "body": RESUME}
    )
    return response.json()


def _proposes(document_id: str, reply: str, interrupt_id: str = "i-1") -> list:
    """career-consultant proposing TAILOR for the document, publishing the changeset
    propose_changeset stored, then replying"""
    stored: dict[str, str] = {}

    def answered(sent: dict) -> dict:
        stored["changeset_id"] = sent["params"]["message"]["parts"][0]["data"][
            "changeset_id"
        ]
        return a2a_accepted()

    def replied(sent: dict) -> list:
        return [
            stream_task(),
            stream_chunk(
                "changeset-1",
                "changeset",
                {"data": {"document_id": document_id} | stored},
            ),
            stream_status("COMPLETED", [{"text": reply}], f"reply-{interrupt_id}"),
        ]

    request = {
        "execute_tool": "propose_changeset",
        "document_id": document_id,
        "changeset": TAILOR,
    }
    return [
        *a2a_turn(
            stream_status("INPUT_REQUIRED", [interrupt_part(request, interrupt_id)])
        ),
        answered,
        replied,
    ]


async def test_a_turn_stores_the_edits_it_proposes_and_announces_them(client, harness):
    document = await _document(client)

    response = await ask(
        client,
        harness,
        "Mention my years",
        *_proposes(document["id"], "I added your years of experience."),
        agent="career-consultant",
        document_id=document["id"],
    )

    [stored] = (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json()
    assert stored["changeset"]["status"] == "pending"
    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {
            "status": "changeset",
            "document_id": document["id"],
            "changeset_id": stored["id"],
            "created_at": stored["created_at"],
        },
        {"status": "completed", "reply": "I added your years of experience."},
    ]
    first, results = (sent["message"] for sent in sent_messages(harness))
    assert harness.received[0].url.path == "/ezcareer/a2a/career-consultant"
    assert first["contextId"] == await thread_of(
        client, "career-consultant", document["id"]
    )
    assert first["parts"][0] == {"text": "Mention my years"}
    data = first["parts"][1]["data"]
    assert data.keys() == {"document_id", "profile_facts", "preferences"}
    assert data["document_id"] == document["id"]
    assert results["parts"] == [interrupt_part({"changeset_id": stored["id"]}, "i-1")]


async def test_a_second_turns_edits_join_the_pending_changeset(client, harness):
    document = await _document(client)
    for interrupt_id in ("i-1", "i-2"):
        await ask(
            client,
            harness,
            "Again",
            *_proposes(document["id"], "Done.", interrupt_id),
            agent="career-consultant",
            document_id=document["id"],
        )

    [stored] = (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json()
    assert len(stored["changeset"]["edits"]) == 2


async def test_edits_that_do_not_fit_the_draft_are_refused_back_to_the_agent(
    client, harness
):
    document = await _document(client)
    misfit = TAILOR | {"edits": [TAILOR["edits"][0] | {"path": "blocks/missing/text"}]}
    request = {
        "execute_tool": "propose_changeset",
        "document_id": document["id"],
        "changeset": misfit,
    }

    await ask(
        client,
        harness,
        "Edit it",
        *a2a_turn(stream_status("INPUT_REQUIRED", [interrupt_part(request)])),
        *a2a_turn(stream_status("COMPLETED", [{"text": "Sorry."}], "reply-1")),
        agent="career-consultant",
        document_id=document["id"],
    )

    [refused] = sent_messages(harness)[1]["message"]["parts"]
    assert set(refused["data"]) == {"error"}
    assert (await client.get(f"{DOCUMENTS}/{document['id']}/changesets")).json() == []


async def test_a_turn_that_fails_before_replying_stays_in_its_documents_chat(
    client, harness
):
    document = await _document(client)

    await ask(
        client,
        harness,
        "Edit it",
        *a2a_turn(stream_status("FAILED", [{"text": "Invalid input"}])),
        agent="career-consultant",
        document_id=document["id"],
    )

    thread = await thread_of(client, "career-consultant", document["id"])
    page = await client.get(f"{PREFIX}/agent/threads/{thread}/messages")
    assert [(m["role"], m["failure"]) for m in page.json()["messages"]] == [
        ("user", None),
        ("agent", "Invalid input"),
    ]


async def test_each_document_has_its_own_thread_and_only_career_consultant_has_one(
    client,
):
    first, second = [await _document(client) for _ in range(2)]
    sessions = f"{PREFIX}/agent/sessions"

    threads = [
        await thread_of(client, "career-consultant", document["id"])
        for document in (first, second, first)
    ]
    without = await client.get(f"{sessions}/career-consultant")
    director = await client.get(
        f"{sessions}/career-director", params={"document_id": first["id"]}
    )

    assert threads[0] == threads[2] != threads[1]
    assert await thread_of(client) not in threads
    assert (without.status_code, director.status_code) == (422, 422)


async def test_clearing_a_documents_conversation_leaves_the_others(client, harness):
    first, second = [await _document(client) for _ in range(2)]
    before = [
        await thread_of(client, "career-consultant", d["id"]) for d in (first, second)
    ]

    cleared = await client.post(
        f"{PREFIX}/agent/sessions/career-consultant/threads",
        params={"document_id": first["id"]},
    )

    after = [
        await thread_of(client, "career-consultant", d["id"]) for d in (first, second)
    ]
    assert cleared.status_code == 201
    assert after[0] == cleared.json()["thread_id"] != before[0]
    assert after[1] == before[1]


async def test_a_documents_thread_lists_every_message_on_it(client, harness):
    document = await _document(client)
    for text in ("One", "Two"):
        await ask(
            client,
            harness,
            text,
            *a2a_turn(
                stream_status("COMPLETED", [{"text": f"Re {text}"}], f"reply-{text}")
            ),
            agent="career-consultant",
            document_id=document["id"],
        )
    thread = await thread_of(client, "career-consultant", document["id"])

    page = (await client.get(f"{PREFIX}/agent/threads/{thread}/messages")).json()

    assert [(m["text"], m["document_id"]) for m in page["messages"]] == [
        ("One", document["id"]),
        ("Re One", document["id"]),
        ("Two", document["id"]),
        ("Re Two", document["id"]),
    ]


async def test_a_thread_takes_no_new_message_while_its_turn_runs(app, client, harness):
    document = await _document(client)
    me = (await client.get(f"{PREFIX}/me")).json()
    thread = await thread_of(client, "career-consultant", document["id"])
    await app.state.container.store().create(
        UUID(me["id"]), thread, "career-consultant"
    )

    response = await ask(
        client,
        harness,
        "Again",
        agent="career-consultant",
        document_id=document["id"],
    )

    assert response.status_code == 409
    assert harness.received == []
    messages = (await client.get(f"{PREFIX}/agent/threads/{thread}/messages")).json()
    assert messages == {"messages": [], "has_more": False}


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

    response = await client.get(
        f"{PREFIX}/agent/sessions/career-consultant",
        params={"document_id": str(theirs.id)},
    )

    assert response.status_code == 404
    assert harness.received == []


async def test_stop_cancels_the_threads_running_task(client, harness):
    document = await _document(client)
    thread = await thread_of(client, "career-consultant", document["id"])
    task = {
        "id": "task-1",
        "contextId": thread,
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}, {"result": task}]

    response = await client.delete(f"{PREFIX}/agent/threads/{thread}/tasks/task-1")

    assert response.status_code == 204
    assert [s["method"] for s in a2a_sent(harness)] == ["GetTask", "CancelTask"]
    assert harness.received[0].url.path == "/ezcareer/a2a/career-consultant"


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_document_asked_for_at_once_gets_one_thread_and_the_database_holds_it(
    postgres_app,
):
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=postgres_app), base_url="http://test"
    ) as client:
        document = await _document(client)
        threads = await asyncio.gather(
            *(thread_of(client, "career-consultant", document["id"]) for _ in range(5))
        )
        cleared = await client.post(
            f"{PREFIX}/agent/sessions/career-consultant/threads",
            params={"document_id": document["id"]},
        )
        async with postgres_app.state.session_factory() as session:
            session.add(
                AgentThread(
                    user_id=UUID((await client.get(f"{PREFIX}/me")).json()["id"]),
                    session_id=(
                        await session.get_one(AgentThread, UUID(threads[0]))
                    ).session_id,
                    document_id=UUID(document["id"]),
                )
            )
            with pytest.raises(IntegrityError, match="uq_agent_threads_document"):
                await session.commit()

    assert len(set(threads)) == 1
    assert cleared.json()["thread_id"] != threads[0]


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_clearing_twice_at_once_leaves_one_new_thread(postgres_app):
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=postgres_app), base_url="http://test"
    ) as client:
        document = await _document(client)
        old = await thread_of(client, "career-consultant", document["id"])
        responses = await asyncio.gather(
            *(
                client.post(
                    f"{PREFIX}/agent/sessions/career-consultant/threads",
                    params={"document_id": document["id"]},
                )
                for _ in range(4)
            ),
            *(
                client.post(f"{PREFIX}/agent/sessions/career-director/threads")
                for _ in range(4)
            ),
        )
        consultant = await thread_of(client, "career-consultant", document["id"])
        director = await thread_of(client)
        me = (await client.get(f"{PREFIX}/me")).json()
        async with postgres_app.state.session_factory() as session:
            open_threads = set(
                await session.scalars(
                    select(AgentThread.id).where(
                        AgentThread.user_id == UUID(me["id"]),
                        AgentThread.cleared_at.is_(None),
                    )
                )
            )

    assert [r.status_code for r in responses] == [201] * 8
    assert consultant != old
    assert open_threads == {UUID(consultant), UUID(director)}
