from uuid import uuid4

import httpx2
import pytest

from tests.conftest import (
    a2a_replied,
    a2a_task,
    a2a_turn,
    ask,
    interrupt_part,
    sent_messages,
    stream_status,
    work,
)
from tests.core.conftest import DATABASE_URL
from tests.features.jobs.test_tailor import (
    DOCUMENTS,
    JOB,
    JOBS,
    LINE,
    RESUME,
    RESUME_EDITS,
    _follow,
    _replies_on_each_thread,
)


async def _copy(client, harness, request: dict, interrupt_id: str) -> dict:
    """What ops-api resumed career-consultant's paused copy_for_job with"""
    await ask(
        client,
        harness,
        "Tailor my résumé",
        *a2a_turn(
            stream_status("INPUT_REQUIRED", [interrupt_part(request, interrupt_id)])
        ),
        *a2a_replied("Copied."),
    )
    return sent_messages(harness)[-1]["message"]["parts"][0]["data"]


def _request(
    document_id: str, job_id: str, copy_id: str, start_over: bool = False
) -> dict:
    """career-consultant's copy_for_job request"""
    return {
        "execute_tool": "copy_for_job",
        "document_id": document_id,
        "job_id": job_id,
        "start_over": start_over,
        "copy_id": copy_id,
    }


async def _resume(client, title: str = "Backend résumé") -> dict:
    """Create a résumé"""
    return (await client.post(DOCUMENTS, json={"title": title, "body": RESUME})).json()


async def test_a_document_is_copied_for_the_job_with_its_posting(client, harness):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())

    answer = await _copy(
        client, harness, _request(resume["id"], job_id, copy_id), "i-1"
    )

    copy = (await client.get(f"{DOCUMENTS}/{copy_id}")).json()
    assert answer == {
        "title": "Backend résumé for Northwind Labs",
        "document_id": copy_id,
        "document": resume["body"],
        "pdf_lines": [],
        "job_id": job_id,
        "job": {
            "title": JOB["title"],
            "company": JOB["company"],
            "location": "",
            "url": JOB["url"],
            "requirements": [
                {
                    "text": "5+ years building backend services",
                    "importance": "required",
                    "match": "met",
                    "reason": "About 7 years across 3 roles",
                },
                {
                    "text": "Kafka or another event bus",
                    "importance": "nice_to_have",
                    "match": "not_met",
                    "reason": "Not in the profile",
                },
                {
                    "text": "Kubernetes in production",
                    "importance": "required",
                    "match": "partly",
                    "reason": "",
                },
            ],
        },
        "made": True,
        "rejected_changeset": False,
    }
    assert copy["title"] == "Backend résumé for Northwind Labs"
    assert copy["body"] == resume["body"]


async def test_asking_again_for_the_same_copy_returns_it_without_a_second(
    client, harness
):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    request = _request(resume["id"], job_id, str(uuid4()))

    first = await _copy(client, harness, request, "i-1")
    again = await _copy(client, harness, request, "i-2")

    assert again == first
    assert len((await client.get(DOCUMENTS)).json()) == 2


async def test_a_document_already_the_jobs_is_returned_itself_with_the_posting(
    client, harness
):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    first = await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")

    again = await _copy(client, harness, _request(copy_id, job_id, str(uuid4())), "i-2")

    assert again == first | {"made": False}
    assert len((await client.get(DOCUMENTS)).json()) == 2


async def test_reading_a_jobs_copy_gives_the_job_it_is_for(client, harness):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")

    read = await _copy(
        client,
        harness,
        {"execute_tool": "read_document", "document_id": copy_id},
        "i-2",
    )

    assert (read["title"], read["job_id"]) == (
        "Backend résumé for Northwind Labs",
        job_id,
    )


async def _edit(client, document_id: str, summary: str) -> dict:
    """Rewrite the document's summary as the user"""
    return (
        await client.post(
            f"{DOCUMENTS}/{document_id}/edits",
            json={
                "edits": [
                    {
                        "kind": "update_field",
                        "path": "blocks/sum/text",
                        "value": {"html": summary, "src": [f"user:{document_id}"]},
                    }
                ]
            },
        )
    ).json()


def _summary(body: dict) -> str:
    """The résumé's summary text"""
    return next(b for b in body["content"]["blocks"] if b["id"] == "sum")["text"][
        "html"
    ]


async def test_a_job_with_a_copy_of_the_kind_returns_that_copy(client, harness):
    resume = await _resume(client)
    other = await _resume(client, "Frontend résumé")
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
    edited = await _edit(client, copy_id, "Tailored for Northwind.")

    answer = await _copy(
        client, harness, _request(other["id"], job_id, str(uuid4())), "i-2"
    )

    assert (answer["document_id"], answer["title"], answer["made"]) == (
        copy_id,
        "Backend résumé for Northwind Labs",
        False,
    )
    assert answer["document"] == edited["body"]
    assert len((await client.get(DOCUMENTS)).json()) == 3
    assert len((await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()) == 1


async def test_start_over_keeps_the_copys_draft_then_resets_it_once_per_call(
    client, harness
):
    resume = await _resume(client)
    master = await _resume(client, "Master résumé")
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
    edited = await _edit(client, copy_id, "Tailored for Northwind.")
    reset = _request(master["id"], job_id, str(uuid4()), start_over=True)

    answer = await _copy(client, harness, reset, "i-2")
    await _edit(client, copy_id, "Tailored again.")
    again = await _copy(client, harness, reset, "i-3")

    assert (answer["document_id"], answer["document"], answer["made"]) == (
        copy_id,
        master["body"],
        False,
    )
    versions = (await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()
    assert [v["label"] for v in versions] == [
        "Before starting over from Master résumé",
        "Copied from Backend résumé",
    ]
    assert again["document_id"] == copy_id
    assert _summary(again["document"]) == "Tailored again."
    restored = await client.post(
        f"{DOCUMENTS}/{copy_id}/versions/{versions[0]['id']}/restore"
    )
    assert _summary(restored.json()["body"]) == _summary(edited["body"])


async def test_start_over_on_the_jobs_own_copy_starts_over_from_its_master(
    client, harness
):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
    await _edit(client, copy_id, "Tailored for Northwind.")
    reset = _request(copy_id, job_id, str(uuid4()), start_over=True)

    answer = await _copy(client, harness, reset, "i-2")
    await _edit(client, copy_id, "Tailored again.")
    again = await _copy(client, harness, reset, "i-3")

    assert (answer["document_id"], answer["document"]) == (copy_id, resume["body"])
    versions = (await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()
    assert [v["label"] for v in versions] == [
        "Before starting over from Backend résumé",
        "Copied from Backend résumé",
    ]
    assert again["document_id"] == copy_id
    assert _summary(again["document"]) == "Tailored again."


async def test_starting_over_rejects_the_copys_pending_changeset(client, harness):
    resume = await _resume(client)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    copy_id = str(uuid4())
    await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
    pending = (
        await client.post(f"{DOCUMENTS}/{copy_id}/changesets", json=RESUME_EDITS)
    ).json()

    answer = await _copy(
        client,
        harness,
        _request(copy_id, job_id, str(uuid4()), start_over=True),
        "i-2",
    )

    assert answer["rejected_changeset"] is True
    [rejected] = (await client.get(f"{DOCUMENTS}/{copy_id}/changesets")).json()
    assert (rejected["id"], rejected["changeset"]["status"]) == (
        pending["id"],
        "rejected",
    )
    assert (await client.get(f"{DOCUMENTS}/{copy_id}")).json()["pending_body"] is None


async def test_a_job_that_is_not_the_users_is_refused(client, harness):
    resume = await _resume(client)

    refused = await _copy(
        client, harness, _request(resume["id"], str(uuid4()), str(uuid4())), "i-1"
    )

    assert refused == {"error": "No such job"}
    assert len((await client.get(DOCUMENTS)).json()) == 1


async def _import(app, client, harness) -> dict:
    """Import a résumé from a PDF with one line"""
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
    return imported


async def test_a_copy_cites_the_lines_of_the_document_it_was_copied_from(
    app, client, harness
):
    imported = await _import(app, client, harness)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]

    answer = await _copy(
        client, harness, _request(imported["id"], job_id, str(uuid4())), "i-1"
    )

    assert answer["pdf_lines"] == [LINE]
    assert (await client.get(f"{DOCUMENTS}/{answer['document_id']}")).json()[
        "lines"
    ] == [{"id": "p1.s1", "text": "Kelvin Chong"}]


async def test_a_copy_reset_from_another_jobs_copy_cites_the_imports_lines(
    app, client, harness
):
    imported = await _import(app, client, harness)
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    other_job_id = (
        await client.post(JOBS, json={**JOB, "url": "https://jobs.example.com/2"})
    ).json()["id"]
    copy_id = str(uuid4())
    other_copy_id = str(uuid4())
    await _copy(client, harness, _request(imported["id"], job_id, copy_id), "i-1")
    await _copy(client, harness, _request(copy_id, other_job_id, other_copy_id), "i-2")

    answer = await _copy(
        client,
        harness,
        _request(other_copy_id, job_id, str(uuid4()), start_over=True),
        "i-3",
    )

    assert (answer["document_id"], answer["pdf_lines"]) == (copy_id, [LINE])
    for document_id in (copy_id, other_copy_id):
        assert (await client.get(f"{DOCUMENTS}/{document_id}")).json()["lines"] == [
            {"id": "p1.s1", "text": "Kelvin Chong"}
        ]


async def test_a_copy_made_from_a_jobs_copy_set_as_master_cites_the_imports_lines(
    app, client, harness
):
    imported = await _import(app, client, harness)
    await client.put(f"{DOCUMENTS}/{imported['id']}/master")
    job_id = (await client.post(JOBS, json=JOB)).json()["id"]
    other_job_id = (
        await client.post(JOBS, json={**JOB, "url": "https://jobs.example.com/2"})
    ).json()["id"]
    harness.outcomes = [_replies_on_each_thread] * 4
    copy_id = (await client.post(f"{JOBS}/{job_id}/tailor")).json()["resume"][
        "document_id"
    ]
    await _follow(client, copy_id)
    await client.put(f"{DOCUMENTS}/{copy_id}/master")
    other_copy_id = (await client.post(f"{JOBS}/{other_job_id}/tailor")).json()[
        "resume"
    ]["document_id"]
    await _follow(client, other_copy_id)

    answer = await _copy(
        client,
        harness,
        _request(other_copy_id, job_id, str(uuid4()), start_over=True),
        "i-1",
    )
    again = await _copy(
        client, harness, _request(copy_id, job_id, str(uuid4()), start_over=True), "i-2"
    )

    assert (answer["document_id"], answer["pdf_lines"]) == (copy_id, [LINE])
    assert (again["document_id"], again["pdf_lines"]) == (copy_id, [LINE])
    versions = (await client.get(f"{DOCUMENTS}/{copy_id}/versions")).json()
    assert versions[0]["label"] == f"Before starting over from {imported['title']}"
    for document_id in (copy_id, other_copy_id):
        assert (await client.get(f"{DOCUMENTS}/{document_id}")).json()["lines"] == [
            {"id": "p1.s1", "text": "Kelvin Chong"}
        ]


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_copy_whose_source_was_deleted_has_no_lines_not_the_masters(
    postgres_app, harness
):
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=postgres_app), base_url="http://test"
    ) as client:
        master = await _import(postgres_app, client, harness)
        await client.put(f"{DOCUMENTS}/{master['id']}/master")
        resume = await _resume(client)
        job_id = (await client.post(JOBS, json=JOB)).json()["id"]
        copy_id = str(uuid4())
        await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")

        await client.delete(f"{DOCUMENTS}/{resume['id']}")

        assert (await client.get(f"{DOCUMENTS}/{copy_id}")).json()["lines"] == []


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_starting_over_a_copy_whose_source_was_deleted_is_refused(
    postgres_app, harness
):
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=postgres_app), base_url="http://test"
    ) as client:
        resume = await _resume(client)
        job_id = (await client.post(JOBS, json=JOB)).json()["id"]
        copy_id = str(uuid4())
        await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
        await client.delete(f"{DOCUMENTS}/{resume['id']}")

        refused = await _copy(
            client,
            harness,
            _request(copy_id, job_id, str(uuid4()), start_over=True),
            "i-2",
        )

        assert refused == {
            "error": "The document this copy was made from is deleted, so there is"
            " nothing to start over from"
        }


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_retried_start_over_succeeds_after_its_source_was_deleted(
    postgres_app, harness
):
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=postgres_app), base_url="http://test"
    ) as client:
        resume = await _resume(client)
        job_id = (await client.post(JOBS, json=JOB)).json()["id"]
        copy_id = str(uuid4())
        await _copy(client, harness, _request(resume["id"], job_id, copy_id), "i-1")
        reset = _request(copy_id, job_id, str(uuid4()), start_over=True)
        first = await _copy(client, harness, reset, "i-2")
        await client.delete(f"{DOCUMENTS}/{resume['id']}")

        again = await _copy(client, harness, reset, "i-3")

        assert again == first
