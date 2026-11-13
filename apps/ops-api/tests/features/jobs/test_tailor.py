from tests.conftest import (
    PREFIX,
    a2a_sent,
    a2a_task,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
    work,
)

JOBS = f"{PREFIX}/jobs"
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

LETTER = {
    "kind": "cover_letter",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}},
            {
                "kind": "letter",
                "id": "letter",
                "greeting": {"text": "Dear hiring team,"},
                "paragraphs": [
                    {"id": "p1", "text": {"html": "I would like to apply."}}
                ],
                "closing": {"text": "Yours sincerely,"},
            },
        ]
    },
}

JOB = {
    "title": "Senior Backend Engineer",
    "company": "Northwind Labs",
    "url": "https://jobs.example.com/1",
    "analysis": {
        "fit": 67,
        "requirements": [
            {
                "text": "5+ years building backend services",
                "match": "met",
                "reason": "About 7 years across 3 roles",
            },
            {
                "text": "Kafka or another event bus",
                "importance": "nice_to_have",
                "match": "not_met",
                "reason": "Not in the profile",
            },
            {"text": "Kubernetes in production", "match": "partly"},
        ],
    },
}

RESUME_EDITS = {
    "id": "tailor-resume",
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

LETTER_EDITS = {
    "id": "tailor-letter",
    "agent": "career-consultant",
    "reason": "Address Northwind Labs.",
    "edits": [
        {
            "kind": "update_field",
            "path": "blocks/letter/greeting",
            "value": {"text": "Dear Northwind Labs team,", "src": ["fact:role-1"]},
        }
    ],
}

WIDGET = {"label": "Did you use Kafka at work?", "submit_btn": "Send"}


def _proposed(changeset: dict) -> list[dict]:
    """edit-document's streamed turn replying with changeset"""
    return [
        stream_task(),
        stream_chunk(
            "a-1",
            "edit-document",
            {"data": {"reply": "Tailored to the posting.", "changeset": changeset}},
        ),
        stream_status("COMPLETED"),
    ]


async def _follow(client, document_id: str) -> list[dict]:
    """The document chat's turn, read from its stream until it ends"""
    return sse_events(await client.get(f"{DOCUMENTS}/{document_id}/chat/stream"))


async def _master(client, title: str, body: dict) -> dict:
    """Create a document and mark it the master of its kind"""
    created = (await client.post(DOCUMENTS, json={"title": title, "body": body})).json()
    return (await client.put(f"{DOCUMENTS}/{created['id']}/master")).json()


async def _job(client) -> str:
    """Store the Northwind Labs posting with its analysis"""
    return (await client.post(JOBS, json=JOB)).json()["id"]


async def test_without_a_master_resume_nothing_is_tailored(client, harness):
    job_id = await _job(client)

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 409
    assert "master résumé" in response.json()["detail"]
    assert harness.received == []
    assert (await client.get(DOCUMENTS)).json() == []


async def test_a_copy_shows_the_lines_of_its_masters_import(app, client, harness):
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
                        "lines": [
                            {
                                "id": "p1.s1",
                                "text": "Kelvin Chong",
                                "page": 1,
                                "x0": 72.0,
                                "top": 60.5,
                                "x1": 180.25,
                                "bottom": 74.0,
                            }
                        ],
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
    await client.put(f"{DOCUMENTS}/{imported['id']}/master")
    job_id = await _job(client)
    harness.outcomes = [_proposed(RESUME_EDITS)]

    tailored = (await client.post(f"{JOBS}/{job_id}/tailor")).json()

    copy = (await client.get(f"{DOCUMENTS}/{tailored['resume']['document_id']}")).json()
    assert copy["lines"] == [{"id": "p1.s1", "text": "Kelvin Chong"}]
    await _follow(client, copy["id"])


async def test_tailoring_copies_each_master_and_starts_its_chat_turn(client, harness):
    resume = await _master(client, "Master résumé", RESUME)
    letter = await _master(client, "Master letter", LETTER)
    job_id = await _job(client)
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [_proposed(RESUME_EDITS), _proposed(LETTER_EDITS)]

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 200
    tailored = response.json()
    assert tailored["resume"]["tailoring"] is True
    assert tailored["cover_letter"]["tailoring"] is True
    copy_id = tailored["resume"]["document_id"]
    letter_id = tailored["cover_letter"]["document_id"]
    assert (await _follow(client, copy_id))[-1] == {
        "status": "completed",
        "reply": "Tailored to the posting.",
    }
    await _follow(client, letter_id)
    listed = {d["id"]: d for d in (await client.get(DOCUMENTS)).json()}
    assert (
        listed[copy_id]["title"],
        listed[copy_id]["master"],
        listed[copy_id]["pending_changesets"],
    ) == ("Résumé for Northwind Labs", False, 1)
    assert listed[letter_id]["title"] == "Cover letter for Northwind Labs"
    assert listed[letter_id]["pending_changesets"] == 1
    assert listed[resume["id"]]["pending_changesets"] == 0
    assert listed[letter["id"]]["pending_changesets"] == 0
    versions = (await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()
    assert [v["label"] for v in versions] == ["Copied from Master résumé"]
    sent = {
        m["contextId"]: m for m in (s["params"]["message"] for s in a2a_sent(harness))
    }
    first = sent[f"{me['id']}:document:{copy_id}"]
    assert first["parts"][0]["text"] == (
        "Tailor this résumé to the Senior Backend Engineer role at Northwind Labs.\n"
        "The posting: https://jobs.example.com/1\n"
        "\n"
        "The posting's requirements:\n"
        "- 5+ years building backend services (required)\n"
        "- Kafka or another event bus (nice to have)\n"
        "- Kubernetes in production (required)\n"
        "\n"
        "Gaps to close where the profile supports it:\n"
        "- Kafka or another event bus (not met). Not in the profile\n"
        "- Kubernetes in production (partly)."
    )
    assert first["parts"][1]["data"]["document_id"] == copy_id
    second = sent[f"{me['id']}:document:{letter_id}"]
    assert second["parts"][0]["text"].startswith("Tailor this cover letter to")


async def test_without_a_master_letter_only_the_resume_is_tailored(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = [_proposed(RESUME_EDITS)]

    response = await client.post(f"{JOBS}/{job_id}/tailor")
    await _follow(client, response.json()["resume"]["document_id"])

    assert response.json()["cover_letter"] is None
    assert response.json()["resume"]["tailoring"] is True
    assert len(harness.received) == 1


async def test_no_copy_is_made_when_the_user_keeps_ten_resumes(client, harness):
    await _master(client, "Master résumé", RESUME)
    for number in range(9):
        await client.post(DOCUMENTS, json={"title": f"Résumé {number}", "body": RESUME})
    job_id = await _job(client)

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "You already keep 10 resume documents. Delete one to add another."
    }
    assert harness.received == []
    assert len((await client.get(DOCUMENTS)).json()) == 10


async def test_no_turn_starts_when_the_cover_letter_has_no_room(client, harness):
    await _master(client, "Master résumé", RESUME)
    await _master(client, "Master letter", LETTER)
    for number in range(9):
        await client.post(DOCUMENTS, json={"title": f"Letter {number}", "body": LETTER})
    job_id = await _job(client)

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 409
    assert harness.received == []


async def test_tailoring_again_reuses_the_jobs_copy(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = [_proposed(RESUME_EDITS)]
    first = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    document_id = first["document_id"]
    await _follow(client, document_id)

    waiting = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    [changeset] = (await client.get(f"{DOCUMENTS}/{document_id}/changesets")).json()
    await client.put(
        f"{DOCUMENTS}/{document_id}/changesets/{changeset['id']}",
        json={"status": "rejected"},
    )
    harness.outcomes = [_proposed(RESUME_EDITS)]
    again = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    await _follow(client, document_id)

    assert waiting == {"document_id": document_id, "tailoring": False}
    assert again == {"document_id": document_id, "tailoring": True}
    assert len(harness.received) == 2
    assert len((await client.get(DOCUMENTS)).json()) == 2


async def test_a_question_is_answered_in_the_copys_chat(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": WIDGET}])]
    ]
    document_id = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"][
        "document_id"
    ]
    asked = await _follow(client, document_id)
    harness.outcomes = [_proposed(RESUME_EDITS)]

    done = await client.post(
        f"{DOCUMENTS}/{document_id}/chat/tasks/task-1/answer",
        json={"input": "Yes, at Acme"},
    )

    assert asked[-1]["status"] == "input_required"
    assert asked[-1]["widget"]["label"] == WIDGET["label"]
    assert sse_events(done)[-1] == {
        "status": "completed",
        "reply": "Tailored to the posting.",
    }
    first, answer = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert answer["taskId"] == "task-1"
    assert answer["contextId"] == first["contextId"]
