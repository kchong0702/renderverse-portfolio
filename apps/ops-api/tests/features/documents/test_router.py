from base64 import b64decode
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.core.auth.models import User
from src.features.documents.models import Document, DocumentImport
from tests.conftest import PREFIX

DOCUMENTS = f"{PREFIX}/documents"

RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}},
            {"kind": "summary", "id": "sum", "text": {"html": "Backend engineer."}},
            {
                "kind": "experience",
                "id": "exp",
                "items": [
                    {
                        "id": "acme",
                        "role": {"text": "Senior Engineer"},
                        "company": {"text": "Acme Corp"},
                        "bullets": [{"id": "b1", "text": {"html": "Led a migration."}}],
                    }
                ],
            },
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
        },
        {
            "kind": "update_field",
            "path": "blocks/exp/items/acme/bullets/b1/text",
            "value": {
                "html": "Moved 30 services to Kubernetes.",
                "src": ["fact:role-1"],
            },
        },
    ],
}


async def _create(client, title="Master résumé", body=RESUME):
    response = await client.post(DOCUMENTS, json={"title": title, "body": body})
    assert response.status_code == 201, response.text
    return response.json()


def _block(document, block_id):
    return next(b for b in document["body"]["content"]["blocks"] if b["id"] == block_id)


async def test_a_user_keeps_at_most_ten_documents_of_each_kind(client):
    for number in range(10):
        await _create(client, title=f"Résumé {number}")

    eleventh = await client.post(DOCUMENTS, json={"title": "One more", "body": RESUME})

    assert eleventh.status_code == 409
    assert eleventh.json() == {
        "detail": "You already keep 10 resume documents. Delete one to add another."
    }
    assert len((await client.get(DOCUMENTS)).json()) == 10


async def test_documents_start_empty(client):
    response = await client.get(DOCUMENTS)

    assert response.status_code == 200
    assert response.json() == []


async def test_create_read_rename_and_list(client):
    created = await _create(client)
    assert created["kind"] == "resume"
    assert created["master"] is False
    assert created["pending_changesets"] == 0
    assert created["body"]["design"]["template"] == "classic"

    renamed = await client.patch(
        f"{DOCUMENTS}/{created['id']}", json={"title": "Résumé for Lumen Pay"}
    )
    assert renamed.json()["title"] == "Résumé for Lumen Pay"
    read = (await client.get(f"{DOCUMENTS}/{created['id']}")).json()
    assert (read["title"], read["body"]) == ("Résumé for Lumen Pay", created["body"])

    listed = (await client.get(DOCUMENTS)).json()
    assert [(d["id"], d["title"]) for d in listed] == [
        (created["id"], "Résumé for Lumen Pay")
    ]
    assert "body" not in listed[0]

    versions = (await client.get(f"{DOCUMENTS}/{created['id']}/versions")).json()
    assert [(v["number"], v["label"]) for v in versions] == [(1, "Created")]


async def test_rejects_a_body_document_schema_refuses(client):
    two_profiles = {
        "kind": "resume",
        "content": {"blocks": [RESUME["content"]["blocks"][0]] * 2},
    }

    response = await client.post(
        DOCUMENTS, json={"title": "Broken", "body": two_profiles}
    )

    assert response.status_code == 422


async def test_user_edits_change_the_draft(client):
    document = await _create(client)
    design = {**document["body"]["design"], "template": "serif", "accent": "#7A1F2B"}

    response = await client.post(
        f"{DOCUMENTS}/{document['id']}/edits",
        json={
            "edits": [
                {
                    "kind": "update_field",
                    "path": "blocks/profile/name",
                    "value": {"text": "Kelvin C.", "src": [f"user:{document['id']}"]},
                },
                {"kind": "update_design", "design": design},
            ]
        },
    )

    assert response.status_code == 200
    assert _block(response.json(), "profile")["name"]["text"] == "Kelvin C."
    assert response.json()["body"]["design"]["template"] == "serif"
    bad = await client.post(
        f"{DOCUMENTS}/{document['id']}/edits",
        json={"edits": [{"kind": "delete", "path": "blocks/nowhere"}]},
    )
    assert bad.status_code == 422


async def test_one_master_per_kind(client):
    first = await _create(client, "Master résumé")
    second = await _create(client, "Résumé for Lumen Pay")

    await client.put(f"{DOCUMENTS}/{first['id']}/master")
    response = await client.put(f"{DOCUMENTS}/{second['id']}/master")

    assert response.json()["master"] is True
    listed = (await client.get(DOCUMENTS)).json()
    assert [(d["title"], d["master"]) for d in listed] == [
        ("Résumé for Lumen Pay", True),
        ("Master résumé", False),
    ]


async def test_keep_and_restore_a_version(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}"
    kept = await client.post(f"{url}/versions", json={"label": "Sent to Lumen Pay"})
    assert kept.status_code == 201
    assert kept.json()["number"] == 2
    await client.post(
        f"{url}/edits",
        json={"edits": [{"kind": "delete", "path": "blocks/sum"}]},
    )

    restored = await client.post(f"{url}/versions/{kept.json()['id']}/restore")

    assert restored.status_code == 200
    assert _block(restored.json(), "sum")["text"]["html"] == "Backend engineer."
    versions = (await client.get(f"{url}/versions")).json()
    assert [v["label"] for v in versions] == [
        "Before restoring version 2",
        "Sent to Lumen Pay",
        "Created",
    ]


async def test_accepting_a_changeset_applies_every_edit_and_can_be_undone(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}"
    proposed = await client.post(f"{url}/changesets", json=TAILOR)
    assert proposed.status_code == 201
    changeset = proposed.json()
    assert changeset["changeset"]["status"] == "pending"
    assert (await client.get(DOCUMENTS)).json()[0]["pending_changesets"] == 1

    accepted = await client.put(
        f"{url}/changesets/{changeset['id']}", json={"status": "accepted"}
    )

    assert accepted.json()["changeset"]["status"] == "accepted"
    draft = (await client.get(url)).json()
    assert _block(draft, "sum")["text"]["html"] == "Backend engineer, 7 years."
    bullet = _block(draft, "exp")["items"][0]["bullets"][0]
    assert bullet["text"]["html"] == "Moved 30 services to Kubernetes."
    assert draft["pending_changesets"] == 0
    versions = (await client.get(f"{url}/versions")).json()
    assert versions[0]["label"] == "Before career-consultant's edits"
    again = await client.put(
        f"{url}/changesets/{changeset['id']}", json={"status": "rejected"}
    )
    assert again.status_code == 409
    listed = (await client.get(f"{url}/changesets")).json()
    assert [c["id"] for c in listed] == [changeset["id"]]
    undone = await client.post(f"{url}/versions/{versions[0]['id']}/restore")
    assert _block(undone.json(), "sum")["text"]["html"] == "Backend engineer."


async def test_rejecting_a_changeset_leaves_the_draft_as_it_was(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}"
    changeset = (await client.post(f"{url}/changesets", json=TAILOR)).json()

    response = await client.put(
        f"{url}/changesets/{changeset['id']}", json={"status": "rejected"}
    )

    assert response.json()["changeset"]["status"] == "rejected"
    assert (await client.get(url)).json()["body"] == document["body"]
    assert len((await client.get(f"{url}/versions")).json()) == 1
    assert (await client.get(url)).json()["pending_changesets"] == 0


async def test_a_new_changeset_closes_the_one_still_pending(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}/changesets"
    first = (await client.post(url, json=TAILOR)).json()
    second = (await client.post(url, json={**TAILOR, "id": "tailor-2"})).json()

    listed = {c["id"]: c["changeset"]["status"] for c in (await client.get(url)).json()}

    assert listed == {first["id"]: "rejected", second["id"]: "pending"}
    assert (await client.get(DOCUMENTS)).json()[0]["pending_changesets"] == 1


async def test_answering_a_changeset_the_same_way_again_is_a_no_op(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}/changesets"
    changeset = (await client.post(url, json=TAILOR)).json()
    await client.put(f"{url}/{changeset['id']}", json={"status": "rejected"})

    again = await client.put(f"{url}/{changeset['id']}", json={"status": "rejected"})

    assert again.status_code == 200
    assert again.json()["changeset"]["status"] == "rejected"


async def test_a_changeset_must_fit_the_draft_and_cite_sources(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}/changesets"
    missing = {**TAILOR, "edits": [{"kind": "delete", "path": "blocks/nowhere"}]}
    unsourced = {
        **TAILOR,
        "edits": [
            {"kind": "update_field", "path": "blocks/sum/text", "value": {"html": "x"}}
        ],
    }

    assert (await client.post(url, json=missing)).status_code == 422
    assert (await client.post(url, json=unsourced)).status_code == 422
    answered = {**TAILOR, "status": "accepted"}
    assert (await client.post(url, json=answered)).status_code == 422


async def test_an_edit_the_user_has_since_removed_conflicts(client):
    document = await _create(client)
    url = f"{DOCUMENTS}/{document['id']}"
    changeset = (await client.post(f"{url}/changesets", json=TAILOR)).json()
    await client.post(
        f"{url}/edits",
        json={
            "edits": [{"kind": "delete", "path": "blocks/exp/items/acme/bullets/b1"}]
        },
    )

    response = await client.put(
        f"{url}/changesets/{changeset['id']}", json={"status": "accepted"}
    )

    assert response.status_code == 409
    listed = (await client.get(f"{url}/changesets")).json()
    assert listed[0]["changeset"]["status"] == "pending"
    draft = (await client.get(url)).json()
    assert _block(draft, "sum")["text"]["html"] == "Backend engineer."


async def test_a_user_keeps_one_master_of_each_kind(app, client):
    first = await _create(client)
    second = await _create(client, title="Second résumé")
    await client.put(f"{DOCUMENTS}/{first['id']}/master")
    await client.put(f"{DOCUMENTS}/{second['id']}/master")

    async with app.state.session_factory() as session:
        stored = await session.get(Document, UUID(first["id"]))
        stored.master = True
        with pytest.raises(IntegrityError):
            await session.commit()

    masters = [d["title"] for d in (await client.get(DOCUMENTS)).json() if d["master"]]
    assert masters == ["Second résumé"]


async def test_documents_of_another_user_are_not_found(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()
    mine = await _create(client)
    async with app.state.session_factory() as session:
        theirs = Document(
            user_id=other.id,
            kind="resume",
            title="Theirs",
            body=(await session.get(Document, UUID(mine["id"]))).body,
        )
        session.add(theirs)
        await session.commit()

    assert [d["title"] for d in (await client.get(DOCUMENTS)).json()] == [
        "Master résumé"
    ]
    for response in (
        await client.get(f"{DOCUMENTS}/{theirs.id}"),
        await client.get(f"{DOCUMENTS}/{theirs.id}/versions"),
        await client.post(f"{DOCUMENTS}/{theirs.id}/changesets", json=TAILOR),
        await client.delete(f"{DOCUMENTS}/{theirs.id}"),
    ):
        assert response.status_code == 404


async def test_templates_and_pdf_come_from_artifact_service(client, artifact):
    document = await _create(client)

    templates = await client.get(f"{DOCUMENTS}/templates", params={"kind": "resume"})
    rendered = await client.get(f"{DOCUMENTS}/{document['id']}/render")

    assert [t["id"] for t in templates.json()] == ["classic"]
    assert rendered.status_code == 200
    assert b64decode(rendered.json()["artifact"]) == b"%PDF-1.7 \xfb\xff"
    assert rendered.json()["report"]["pages"] == 1
    assert artifact.rendered == [{"document": document["body"]}]

    artifact.down = True
    assert (await client.get(f"{DOCUMENTS}/{document['id']}/render")).status_code == 503


async def test_an_upload_is_stored_as_a_pending_import(app, client):
    pdf = b"%PDF-1.7 resume"

    created = await client.post(
        f"{DOCUMENTS}/imports",
        files={"file": ("kelvin-chong-resume.pdf", pdf, "application/pdf")},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["size"] == len(pdf)
    assert created.json()["document_id"] is None
    assert [
        i["filename"] for i in (await client.get(f"{DOCUMENTS}/imports")).json()
    ] == ["kelvin-chong-resume.pdf"]
    async with app.state.session_factory() as session:
        stored = await session.scalar(
            select(DocumentImport.content).where(
                DocumentImport.id == UUID(created.json()["id"])
            )
        )
    assert stored == pdf

    cancelled = await client.delete(f"{DOCUMENTS}/imports/{created.json()['id']}")
    assert cancelled.status_code == 204
    assert (await client.get(f"{DOCUMENTS}/imports")).json() == []


async def test_an_upload_must_be_a_pdf_or_word_file(client):
    image = await client.post(
        f"{DOCUMENTS}/imports", files={"file": ("me.png", b"png", "image/png")}
    )
    empty = await client.post(
        f"{DOCUMENTS}/imports", files={"file": ("cv.pdf", b"", "application/pdf")}
    )

    assert image.status_code == 422
    assert empty.status_code == 422
