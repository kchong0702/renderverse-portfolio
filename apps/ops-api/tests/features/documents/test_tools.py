from uuid import UUID

from src.core.auth.models import User
from src.features.documents.models import Document
from tests.conftest import (
    PREFIX,
    a2a_sent,
    interrupt_part,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
)

DOCUMENTS = f"{PREFIX}/documents"
CHAT = f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f"

RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}}
        ]
    },
}


async def _create(client, title: str, kind: str = "resume") -> dict:
    """Add a document of this kind"""
    response = await client.post(
        DOCUMENTS, json={"title": title, "body": RESUME | {"kind": kind}}
    )
    return response.json()


async def _answer(client, harness, request: dict) -> dict:
    """What ops-api resumed career-director with after it paused on this tool"""
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [interrupt_part(request)])],
        [
            stream_chunk("a-1", "career-director", {"text": "Found it."}),
            stream_status("COMPLETED"),
        ],
    ]
    response = await client.post(f"{CHAT}/messages", json={"text": "Edit my résumé"})
    assert sse_events(response)[-1] == {"status": "completed", "reply": "Found it."}
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]


async def test_documents_are_found_by_a_misspelled_name_best_first(client, harness):
    northwind = await _create(client, "Résumé for Northwind Labs")
    await _create(client, "Résumé for Lumen Pay")
    northwind_cv = await _create(client, "CV for Northwind Labs", "cv")

    answer = await _answer(
        client, harness, {"execute_tool": "documents", "name": "nortwind labs résumé"}
    )

    assert [d.pop("updated_at")[:19] for d in answer["documents"]] == [
        d["updated_at"][:19] for d in (northwind, northwind_cv)
    ]
    assert answer["documents"] == [
        {"id": d["id"], "kind": d["kind"], "title": d["title"], "master": False}
        for d in (northwind, northwind_cv)
    ]


async def test_documents_are_found_by_part_of_a_name_and_their_kind(client, harness):
    await _create(client, "Résumé for Northwind Labs")
    await _create(client, "Résumé for Lumen Pay")
    await _create(client, "CV for Northwind Labs", "cv")

    lumen = await _answer(
        client, harness, {"execute_tool": "documents", "name": "lumen"}
    )
    cv = await _answer(
        client,
        harness,
        {"execute_tool": "documents", "name": "northwind", "kind": "cv"},
    )

    assert [d["title"] for d in lumen["documents"]] == ["Résumé for Lumen Pay"]
    assert [d["title"] for d in cv["documents"]] == ["CV for Northwind Labs"]


async def test_documents_without_a_name_list_the_master_then_the_newest(
    client, harness
):
    master = await _create(client, "Master résumé")
    await client.put(f"{DOCUMENTS}/{master['id']}/master")
    await _create(client, "Résumé for Northwind Labs")
    await _create(client, "Résumé for Lumen Pay")
    await _create(client, "Kelvin's CV", "cv")

    answer = await _answer(
        client, harness, {"execute_tool": "documents", "kind": "resume"}
    )

    assert [d["title"] for d in answer["documents"]] == [
        "Master résumé",
        "Résumé for Lumen Pay",
        "Résumé for Northwind Labs",
    ]


async def test_a_document_of_another_user_is_not_executed(app, client, harness):
    mine = await _create(client, "Master résumé")
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

    answer = await _answer(
        client, harness, {"execute_tool": "document", "id": str(theirs.id)}
    )
    own = await _answer(client, harness, {"execute_tool": "document", "id": mine["id"]})

    assert answer == {"error": "No such document"}
    assert own == {"document": mine["body"], "lines": []}
