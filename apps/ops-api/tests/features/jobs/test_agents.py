from datetime import timedelta
from uuid import UUID, uuid4

from src.db.base import utcnow
from src.db.queue import claim
from src.features.jobs.models import JobRun
from src.features.jobs.processing import JOB_RUNS
from tests.conftest import PREFIX, a2a_sent, a2a_task, work

JOBS = f"{PREFIX}/jobs"

REQUIREMENTS = [
    {
        "text": "5+ years building backend services",
        "importance": "required",
        "line_ids": [4],
        "match": "met",
        "fact_ids": ["fact:role-1"],
        "reason": "About 7 years across 3 roles",
    },
    {
        "text": "Kafka or another event bus",
        "importance": "nice_to_have",
        "line_ids": [7],
        "match": "not_met",
        "fact_ids": [],
        "reason": "Not in the profile",
    },
]

READ_BACK = [
    {key: r[key] for key in ("text", "importance", "match", "reason")}
    for r in REQUIREMENTS
]

MATCHED = {
    "posting": {
        "id": "jsearch-1",
        "title": "Senior Backend Engineer",
        "company": "Northwind Labs",
        "location": "Kuala Lumpur, Malaysia",
        "country": "MY",
        "remote": True,
        "posted_at": "2026-11-07T09:00:00Z",
        "apply_url": "https://jobs.example.com/1",
        "lines": [{"id": 4, "text": "5+ years building backend services"}],
    },
    "requirements": REQUIREMENTS,
    "fit": 67,
}

ANALYSIS = {
    "requirements": REQUIREMENTS,
    "terms": {},
    "url": "https://jobs.example.com/2",
    "lines": [{"id": 4, "text": "5+ years building backend services"}],
    "filters": [],
    "fit": 67,
}


def _found(*jobs: dict) -> dict:
    """find-jobs' reply with these jobs"""
    return a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": list(jobs)}}])


async def _find(client, search: dict | None = None) -> dict:
    """Queue a manual run on the search and return it as queued"""
    queued = await client.post(f"{JOBS}/find", json=search)
    assert queued.status_code == 202
    return queued.json()


async def _latest(client) -> dict:
    """The user's latest run"""
    return (await client.get(f"{JOBS}/runs/latest")).json()


async def _due(app, run_id: str) -> None:
    """Let the run be claimed now, as if its backoff or run_after had passed"""
    async with app.state.session_factory() as session, session.begin():
        row = await session.get(JobRun, UUID(run_id))
        row.run_after = utcnow() - timedelta(seconds=1)


async def test_a_queued_find_run_stores_each_job_found_as_a_pick(app, client, harness):
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [_found(MATCHED)]

    queued = await _find(client)
    await work(app)

    assert (queued["trigger"], queued["status"], queued["found"]) == (
        "manual",
        "queued",
        0,
    )
    done = await _latest(client)
    assert done["id"] == queued["id"]
    assert (done["status"], done["found"], done["new"], done["error"]) == (
        "done",
        1,
        1,
        "",
    )
    assert done["finished_at"] is not None
    [job] = (await client.get(JOBS)).json()["jobs"]
    assert job["external_id"] == "jsearch-1"
    assert job["source"] == "JSearch"
    assert job["location"] == "Kuala Lumpur, Malaysia, remote"
    assert job["url"] == "https://jobs.example.com/1"
    assert job["status"] == "picked"
    assert job["analysis"] == {"fit": 67, "band": "possible", "requirements": READ_BACK}
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/find-jobs"
    message = a2a_sent(harness)[0]["params"]["message"]
    assert message["contextId"].startswith(f"{me['id']}:")
    assert message["parts"] == [{"data": {**agent_profile, "search": None}}]
    assert "metadata" not in a2a_sent(harness)[0]["params"]


async def test_the_search_sent_reaches_find_jobs(app, client, harness):
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    search = {"query": "Staff engineer", "location": "Remote", "posted_within": "week"}
    harness.outcomes = [_found(), _found()]

    await _find(client, search)
    await work(app)
    await _find(client, {"posted_within": "day"})
    await work(app)

    assert [sent["params"]["message"]["parts"] for sent in a2a_sent(harness)] == [
        [{"data": {**agent_profile, "search": search}}],
        [
            {
                "data": {
                    **agent_profile,
                    "search": {"query": None, "location": None, "posted_within": "day"},
                }
            }
        ],
    ]


async def test_a_search_find_jobs_cannot_run_is_refused(client, harness):
    response = await client.post(f"{JOBS}/find", json={"posted_within": "year"})

    assert response.status_code == 422
    assert harness.received == []


async def test_a_run_is_refused_while_one_of_its_trigger_waits_or_a_find_while_one_runs(
    app, client, harness
):
    assert (await client.get(f"{JOBS}/runs/latest")).status_code == 404
    queued = await _find(client)

    find_again = await client.post(f"{JOBS}/find")
    agent = await client.post(f"{JOBS}/runs", json={})
    agent_again = await client.post(f"{JOBS}/runs", json={})
    async with app.state.session_factory() as session, session.begin():
        claimed = await claim(session, JOB_RUNS, timedelta(seconds=60))
    find_while_running = await client.post(f"{JOBS}/find")

    assert (find_again.status_code, agent.status_code, agent_again.status_code) == (
        409,
        202,
        409,
    )
    assert "already queued" in find_again.json()["detail"]
    assert claimed.id == UUID(queued["id"])
    assert find_while_running.status_code == 409
    assert "already running" in find_while_running.json()["detail"]
    assert (await _latest(client))["id"] == agent.json()["id"]
    assert harness.received == []


async def test_a_cancelled_run_never_runs_and_a_taken_one_cannot_be_cancelled(
    app, client, harness
):
    queued = await _find(client)

    cancelled = await client.delete(f"{JOBS}/runs/{queued['id']}")
    await work(app)
    again = await _find(client)
    async with app.state.session_factory() as session, session.begin():
        await claim(session, JOB_RUNS, timedelta(seconds=60))
    taken = await client.delete(f"{JOBS}/runs/{again['id']}")
    missing = await client.delete(f"{JOBS}/runs/{uuid4()}")

    assert cancelled.status_code == 204
    assert harness.received == []
    assert (taken.status_code, missing.status_code) == (409, 404)
    assert (await _latest(client))["id"] == again["id"]


async def test_a_posting_too_long_to_store_is_cut_or_skipped_and_the_run_completes(
    app, client, harness
):
    long_title = {
        **MATCHED,
        "posting": {**MATCHED["posting"], "title": "Senior " * 40},
        "fit": 80,
    }
    long_url = {
        **MATCHED,
        "posting": {
            **MATCHED["posting"],
            "id": "jsearch-2",
            "apply_url": "https://jobs.example.com/" + "x" * 2000,
        },
        "fit": 90,
    }
    harness.outcomes = [_found(long_title, long_url)]

    await _find(client)
    await work(app)

    done = await _latest(client)
    assert (done["status"], done["found"], done["new"], done["matched"]) == (
        "done",
        1,
        1,
        1,
    )
    [job] = (await client.get(JOBS)).json()["jobs"]
    assert job["title"] == ("Senior " * 40)[:200]
    assert job["external_id"] == "jsearch-1"


async def test_matched_counts_the_jobs_at_or_above_the_users_min_score(
    app, client, harness
):
    strong = {
        **MATCHED,
        "posting": {**MATCHED["posting"], "id": "jsearch-2"},
        "fit": 70,
    }
    harness.outcomes = [_found(MATCHED, strong), _found(MATCHED, strong)]

    await _find(client)
    await work(app)
    first = await _latest(client)
    await client.patch(f"{PREFIX}/preferences", json={"min_score": 60})
    await _find(client)
    await work(app)
    second = await _latest(client)

    assert {k: first[k] for k in ("found", "new", "matched")} == {
        "found": 2,
        "new": 2,
        "matched": 1,
    }
    assert {k: second[k] for k in ("found", "new", "matched")} == {
        "found": 2,
        "new": 0,
        "matched": 2,
    }
    assert second["created_at"] > first["created_at"]


async def test_a_failed_search_fails_the_run_with_its_reason_and_stores_nothing(
    app, client, harness
):
    reason = "JSearch did not answer"
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": reason}])]

    await _find(client)
    await work(app)

    failed = await _latest(client)
    assert (failed["status"], failed["error"]) == ("failed", reason)
    assert failed["finished_at"] is not None
    assert (await client.get(JOBS)).json()["jobs"] == []
    harness.outcomes = [_found()]
    await _due(app, failed["id"])
    await work(app)
    assert len(harness.received) == 1


async def test_an_unreachable_harness_queues_the_run_again(app, client, harness):
    harness.down = True

    await _find(client)
    await work(app)

    queued = await _latest(client)
    assert queued["status"] == "queued"
    assert queued["error"] != ""
    harness.down = False
    harness.outcomes = [_found()]
    await work(app)
    assert harness.received == []
    await _due(app, queued["id"])
    await work(app)
    done = await _latest(client)
    assert (done["status"], done["error"]) == ("done", "")


async def test_an_agent_run_waits_until_run_after(app, client, harness):
    later = (utcnow() + timedelta(hours=1)).isoformat()
    harness.outcomes = [_found()]

    queued = await client.post(
        f"{JOBS}/runs", json={"run_after": later, "search": {"query": "Staff"}}
    )
    await work(app)

    assert queued.status_code == 202
    assert (queued.json()["trigger"], queued.json()["status"]) == ("agent", "queued")
    assert harness.received == []
    await _due(app, queued.json()["id"])
    await work(app)
    assert (await _latest(client))["status"] == "done"
    [sent] = a2a_sent(harness)
    assert sent["params"]["message"]["parts"][0]["data"]["search"] == {
        "query": "Staff",
        "location": None,
        "posted_within": None,
    }


async def test_each_run_carries_the_users_model(app, client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})
    job = (
        await client.post(
            JOBS, json={"title": "Platform Engineer", "url": ANALYSIS["url"]}
        )
    ).json()
    harness.outcomes = [
        _found(),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"analysis": ANALYSIS}}]),
    ]

    await _find(client)
    await work(app)
    await client.post(f"{JOBS}/{job['id']}/analyse")

    assert [sent["params"]["metadata"] for sent in a2a_sent(harness)] == [
        {"model": model}
    ] * 2


async def test_a_job_found_again_keeps_its_status(app, client, harness):
    harness.outcomes = [_found(MATCHED), _found(MATCHED)]
    await _find(client)
    await work(app)
    [job] = (await client.get(JOBS)).json()["jobs"]
    await client.patch(f"{JOBS}/{job['id']}", json={"status": "dismissed"})

    await _find(client)
    await work(app)

    assert [j["status"] for j in (await client.get(JOBS)).json()["jobs"]] == [
        "dismissed"
    ]
    assert (await _latest(client))["new"] == 0
    first, second = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert first["contextId"] != second["contextId"]


async def test_analysing_a_job_stores_the_analysis(client, harness):
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    job = (
        await client.post(
            JOBS, json={"title": "Platform Engineer", "url": ANALYSIS["url"]}
        )
    ).json()
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"analysis": ANALYSIS}}])
    ]

    response = await client.post(f"{JOBS}/{job['id']}/analyse")

    assert response.status_code == 200
    analysis = {"fit": 67, "band": "possible", "requirements": READ_BACK}
    assert response.json() == {**job, "analysis": analysis}
    assert (await client.get(JOBS)).json()["jobs"][0]["analysis"] == analysis
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/analyse-job"
    assert a2a_sent(harness)[0]["params"]["message"]["parts"] == [
        {"data": {"url": ANALYSIS["url"], **agent_profile}}
    ]


async def test_a_job_without_a_posting_url_cannot_be_analysed(client, harness):
    job = (await client.post(JOBS, json={"title": "Platform Engineer"})).json()

    response = await client.post(f"{JOBS}/{job['id']}/analyse")

    assert response.status_code == 422
    assert harness.received == []


async def test_a_failed_analysis_returns_its_reason_and_keeps_the_job(client, harness):
    job = (
        await client.post(
            JOBS, json={"title": "Platform Engineer", "url": ANALYSIS["url"]}
        )
    ).json()
    reason = "Couldn't fetch the posting: 404"
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": reason}])]

    response = await client.post(f"{JOBS}/{job['id']}/analyse")

    assert response.status_code == 422
    assert response.json() == {"reason": reason, "next": None}
    assert (await client.get(JOBS)).json()["jobs"] == [job]


async def test_an_unreadable_analysis_gives_a_clear_error(client, harness):
    job = (
        await client.post(
            JOBS, json={"title": "Platform Engineer", "url": ANALYSIS["url"]}
        )
    ).json()
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"analysis": None}}])
    ]

    response = await client.post(f"{JOBS}/{job['id']}/analyse")

    assert response.status_code == 503
    assert (await client.get(JOBS)).json()["jobs"] == [job]
