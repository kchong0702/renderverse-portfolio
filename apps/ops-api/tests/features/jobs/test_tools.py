from tests.conftest import (
    PREFIX,
    a2a_sent,
    interrupt_part,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
)

JOBS = f"{PREFIX}/jobs"
CHAT = f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f"


async def _answer(client, harness, request: dict) -> dict:
    """What ops-api resumed career-director with after it paused on this tool"""
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [interrupt_part(request)])],
        [
            stream_chunk("a-1", "career-director", {"text": "Found them."}),
            stream_status("COMPLETED"),
        ],
    ]
    response = await client.post(f"{CHAT}/messages", json={"text": "Which jobs?"})
    assert sse_events(response)[-1] == {"status": "completed", "reply": "Found them."}
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]


async def _job(client, company: str, status: str) -> dict:
    """Store a job with this status"""
    job = (
        await client.post(JOBS, json={"title": "Engineer", "company": company})
    ).json()
    await client.patch(f"{JOBS}/{job['id']}", json={"status": status})
    return job


async def test_the_jobs_page_jobs_are_listed_and_every_status_counted(client, harness):
    await _job(client, "Harbor Health", "saved")
    await _job(client, "Kopi Cloud", "picked")
    await _job(client, "Lumen Pay", "dismissed")

    answer = await _answer(client, harness, {"execute_tool": "saved_jobs"})

    assert answer["by_status"] == {"picked": 1, "saved": 1, "dismissed": 1}
    assert sorted(job["company"] for job in answer["jobs"]) == [
        "Harbor Health",
        "Kopi Cloud",
    ]
    [harbor] = [job for job in answer["jobs"] if job["company"] == "Harbor Health"]
    assert harbor == {
        "title": "Engineer",
        "company": "Harbor Health",
        "location": "",
        "salary": "",
        "url": "",
        "posted_at": None,
        "status": "saved",
        "fit": None,
    }


async def test_a_company_narrows_the_counts_and_a_status_only_the_list(client, harness):
    await _job(client, "Harbor Health", "dismissed")
    await _job(client, "Harbor Labs", "saved")
    await _job(client, "Kopi Cloud", "saved")

    answer = await _answer(
        client,
        harness,
        {"execute_tool": "saved_jobs", "company": "harbor", "status": "dismissed"},
    )

    assert answer["by_status"] == {"picked": 0, "saved": 1, "dismissed": 1}
    assert [job["company"] for job in answer["jobs"]] == ["Harbor Health"]
