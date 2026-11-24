from uuid import UUID

from src.core.auth.models import User
from src.features.documents.models import Document
from tests.conftest import (
    PREFIX,
    a2a_sent,
    a2a_task,
    interrupt_part,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
    work,
)

DOCUMENTS = f"{PREFIX}/documents"
CHAT = f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f"

LINE = {
    "id": "p1.s1",
    "text": "Kelvin Chong",
    "page": 1,
    "x0": 72.0,
    "top": 60.5,
    "x1": 180.25,
    "bottom": 74.0,
}

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
    assert answer["content"] == {"document": northwind["body"], "pdf_lines": []}


async def test_no_match_comes_with_no_content(client, harness):
    await _create(client, "Résumé for Lumen Pay")

    answer = await _answer(
        client, harness, {"execute_tool": "documents", "name": "zebra"}
    )

    assert answer == {"documents": [], "content": None}


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


async def test_an_imported_best_match_comes_with_its_lines(app, client, harness):
    harness.outcomes = [
        a2a_task(
            "COMPLETED",
            artifact_parts=[
                {
                    "data": {
                        "document": RESUME,
                        "pdf": "JVBERi0=",
                        "report": {
                            "render_id": "0" * 64,
                            "pages": 1,
                            "last_page_fill": 0.4,
                        },
                        "pdf_lines": [LINE],
                        "suggestion": {"template": "serif", "columns": 1, "traits": []},
                    }
                }
            ],
        )
    ]
    await client.post(
        f"{DOCUMENTS}/imports",
        files={"file": ("resume.pdf", b"%PDF-1.7 resume", "application/pdf")},
    )
    await work(app)
    [imported] = (await client.get(DOCUMENTS)).json()

    answer = await _answer(client, harness, {"execute_tool": "documents"})

    assert [d["id"] for d in answer["documents"]] == [imported["id"]]
    assert answer["content"]["pdf_lines"] == [LINE]


async def test_another_users_documents_are_not_found(app, client, harness):
    mine = await _create(client, "Master résumé")
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.flush()
        session.add(
            Document(
                user_id=other.id,
                kind="resume",
                title="Theirs",
                body=(await session.get(Document, UUID(mine["id"]))).body,
            )
        )
        await session.commit()

    answer = await _answer(client, harness, {"execute_tool": "documents"})

    assert [d["id"] for d in answer["documents"]] == [mine["id"]]


async def test_one_document_is_not_executed_on_its_own(client, harness):
    mine = await _create(client, "Master résumé")

    answer = await _answer(
        client, harness, {"execute_tool": "document", "id": mine["id"]}
    )

    assert answer == {"error": "Ops has no document tool"}
