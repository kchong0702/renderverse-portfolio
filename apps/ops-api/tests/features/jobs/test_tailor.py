from uuid import UUID, uuid4

from tests.conftest import (
    PREFIX,
    a2a_accepted,
    a2a_task,
    interrupt_part,
    sent_messages,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
    thread_of,
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

LINE = {
    "id": "p1.s1",
    "text": "Kelvin Chong",
    "page": 1,
    "x0": 72.0,
    "top": 60.5,
    "x1": 180.25,
    "bottom": 74.0,
}


def _tailoring(changeset: dict) -> list:
    """career-consultant's turn on the document it is sent: propose_changeset with
    changeset, then publish the stored changeset and reply"""
    seen: dict[str, str] = {}

    def accepted(sent: dict) -> dict:
        seen["document_id"] = sent["params"]["message"]["parts"][1]["data"][
            "document_id"
        ]
        return a2a_accepted()

    def paused(sent: dict) -> list:
        request = {
            "execute_tool": "propose_changeset",
            "document_id": seen["document_id"],
            "changeset": changeset,
        }
        return [
            stream_task(),
            stream_status("INPUT_REQUIRED", [interrupt_part(request, uuid4().hex)]),
        ]

    def stored(sent: dict) -> dict:
        seen["changeset_id"] = sent["params"]["message"]["parts"][0]["data"][
            "changeset_id"
        ]
        return a2a_accepted()

    def replied(sent: dict) -> list:
        return [
            stream_task(),
            stream_chunk("changeset-1", "changeset", {"data": seen}),
            stream_status(
                "COMPLETED", [{"text": "Tailored to the posting."}], uuid4().hex
            ),
        ]

    return [accepted, paused, stored, replied]


async def _follow(client, document_id: str) -> list[dict]:
    """The document's career-consultant thread's turn, read from its stream until it
    ends"""
    thread = await thread_of(client, "career-consultant", document_id)
    return sse_events(await client.get(f"{PREFIX}/agent/threads/{thread}/stream"))


def _replies_on_each_thread(sent: dict) -> dict | list:
    """The harness taking each thread's message as a task named after the thread and
    replying on it"""
    if sent["method"] == "SendMessage":
        return a2a_accepted(sent["params"]["message"]["contextId"])
    return [
        stream_task(),
        stream_status(
            "COMPLETED", [{"text": "Tailored."}], f"reply-{sent['params']['id']}"
        ),
    ]


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
    await client.put(f"{DOCUMENTS}/{imported['id']}/master")
    job_id = await _job(client)
    harness.outcomes = _tailoring(RESUME_EDITS)

    tailored = (await client.post(f"{JOBS}/{job_id}/tailor")).json()

    copy = (await client.get(f"{DOCUMENTS}/{tailored['resume']['document_id']}")).json()
    assert copy["lines"] == [{"id": "p1.s1", "text": "Kelvin Chong"}]
    await _follow(client, copy["id"])


async def test_tailoring_copies_the_master_and_starts_a_turn_on_the_copys_thread(
    client, harness
):
    resume = await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = _tailoring(RESUME_EDITS)

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 200
    tailored = response.json()
    copy_id = tailored["resume"]["document_id"]
    assert tailored == {
        "resume": {"document_id": copy_id, "tailoring": True},
        "cover_letter": None,
    }
    thread = await thread_of(client, "career-consultant", copy_id)
    events = await _follow(client, copy_id)
    assert events[-2:] == [
        {
            "status": "changeset",
            "document_id": copy_id,
            "changeset_id": events[-2]["changeset_id"],
            "created_at": events[-2]["created_at"],
        },
        {"status": "completed", "reply": "Tailored to the posting."},
    ]
    listed = {d["id"]: d for d in (await client.get(DOCUMENTS)).json()}
    assert (
        listed[copy_id]["title"],
        listed[copy_id]["master"],
        listed[copy_id]["pending_changesets"],
    ) == ("Résumé for Northwind Labs", False, 1)
    assert listed[resume["id"]]["pending_changesets"] == 0
    versions = (await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()
    assert [v["label"] for v in versions] == ["Copied from Master résumé"]
    first = sent_messages(harness)[0]["message"]
    assert first["contextId"] == thread
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
    messages = (await client.get(f"{PREFIX}/agent/threads/{thread}/messages")).json()[
        "messages"
    ]
    assert [(m["role"], m["document_id"]) for m in messages] == [
        ("user", copy_id),
        ("agent", copy_id),
    ]
    assert messages[1]["changesets"] == [
        {
            "id": events[-2]["changeset_id"],
            "document_id": copy_id,
            "created_at": events[-2]["created_at"],
        }
    ]


async def test_the_resume_and_letter_are_tailored_at_once_each_on_its_own_thread(
    client, harness
):
    await _master(client, "Master résumé", RESUME)
    await _master(client, "Master letter", LETTER)
    job_id = await _job(client)
    harness.outcomes = [_replies_on_each_thread] * 4

    tailored = (await client.post(f"{JOBS}/{job_id}/tailor")).json()

    copies = [tailored[kind]["document_id"] for kind in ("resume", "cover_letter")]
    assert [tailored[kind]["tailoring"] for kind in ("resume", "cover_letter")] == [
        True,
        True,
    ]
    threads = [await thread_of(client, "career-consultant", c) for c in copies]
    ended = [(await _follow(client, c))[-1] for c in copies]
    assert ended == [{"status": "completed", "reply": "Tailored."}] * 2
    started = {
        m["message"]["contextId"]: m["message"]["parts"][1]["data"]["document_id"]
        for m in sent_messages(harness)
    }
    assert started == dict(zip(threads, copies, strict=True))
    assert threads[0] != threads[1]
    listed = {d["id"]: d["title"] for d in (await client.get(DOCUMENTS)).json()}
    assert listed[copies[1]] == "Cover letter for Northwind Labs"


async def test_tailoring_skips_only_the_copy_whose_thread_is_busy(app, client, harness):
    await _master(client, "Master résumé", RESUME)
    await _master(client, "Master letter", LETTER)
    job_id = await _job(client)
    harness.outcomes = [_replies_on_each_thread] * 4
    first = (await client.post(f"{JOBS}/{job_id}/tailor")).json()
    for kind in ("resume", "cover_letter"):
        await _follow(client, first[kind]["document_id"])
    me = (await client.get(f"{PREFIX}/me")).json()
    busy = await thread_of(
        client, "career-consultant", first["cover_letter"]["document_id"]
    )
    await app.state.container.store().create(UUID(me["id"]), busy, "career-consultant")
    harness.outcomes = [_replies_on_each_thread] * 2

    again = (await client.post(f"{JOBS}/{job_id}/tailor")).json()

    assert (again["resume"]["tailoring"], again["cover_letter"]["tailoring"]) == (
        True,
        False,
    )
    await _follow(client, again["resume"]["document_id"])


async def test_tailoring_fails_when_a_copys_turn_cannot_start(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)

    def drop(sent: dict) -> list:
        """The stream breaks and the harness is gone"""
        harness.down = True
        return [stream_task(), stream_status("WORKING")]

    harness.outcomes = [a2a_accepted(), drop]
    first = (await client.post(f"{JOBS}/{job_id}/tailor")).json()
    await _follow(client, first["resume"]["document_id"])

    response = await client.post(f"{JOBS}/{job_id}/tailor")

    assert response.status_code == 503
    assert "did not say how the last reply ended" in response.json()["detail"]


async def test_without_a_master_letter_only_the_resume_is_tailored(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = _tailoring(RESUME_EDITS)

    response = await client.post(f"{JOBS}/{job_id}/tailor")
    await _follow(client, response.json()["resume"]["document_id"])

    assert response.json()["cover_letter"] is None
    assert response.json()["resume"]["tailoring"] is True
    assert len(sent_messages(harness)) == 2


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
    harness.outcomes = _tailoring(RESUME_EDITS)
    first = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    document_id = first["document_id"]
    await _follow(client, document_id)

    waiting = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    [changeset] = (await client.get(f"{DOCUMENTS}/{document_id}/changesets")).json()
    await client.put(
        f"{DOCUMENTS}/{document_id}/changesets/{changeset['id']}",
        json={"status": "rejected"},
    )
    harness.outcomes = _tailoring(RESUME_EDITS)
    again = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]
    await _follow(client, document_id)

    assert waiting == {"document_id": document_id, "tailoring": False}
    assert again == {"document_id": document_id, "tailoring": True}
    assert len(sent_messages(harness)) == 4
    assert len((await client.get(DOCUMENTS)).json()) == 2


async def test_a_question_is_answered_on_the_consultant_thread(client, harness):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = [
        a2a_accepted(),
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": WIDGET}])],
    ]
    document_id = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"][
        "document_id"
    ]
    thread = await thread_of(client, "career-consultant", document_id)
    asked = await _follow(client, document_id)
    harness.outcomes = [
        a2a_accepted(),
        [
            stream_task(),
            stream_status(
                "COMPLETED", [{"text": "Tailored to the posting."}], "reply-2"
            ),
        ],
    ]

    done = await client.post(
        f"{PREFIX}/agent/threads/{thread}/tasks/task-1/answer",
        json={"input": "Yes, at Acme"},
    )

    assert asked[-1]["status"] == "input_required"
    assert asked[-1]["widget"]["label"] == WIDGET["label"]
    assert sse_events(done)[-1] == {
        "status": "completed",
        "reply": "Tailored to the posting.",
    }
    first, answer = (sent["message"] for sent in sent_messages(harness))
    assert answer["taskId"] == "task-1"
    assert answer["contextId"] == first["contextId"] == thread


async def test_tailoring_waits_while_the_consultant_thread_asks_the_user(
    client, harness
):
    await _master(client, "Master résumé", RESUME)
    job_id = await _job(client)
    harness.outcomes = [
        a2a_accepted(),
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": WIDGET}])],
    ]
    tailored = (await client.post(f"{JOBS}/{job_id}/tailor")).json()
    await _follow(client, tailored["resume"]["document_id"])
    sent = len(sent_messages(harness))

    again = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"]

    assert again["tailoring"] is False
    assert len(sent_messages(harness)) == sent
