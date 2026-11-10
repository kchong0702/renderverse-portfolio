from tests.conftest import PREFIX, a2a_sent, a2a_task

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


async def test_run_agent_now_stores_each_job_found_as_a_pick(client, harness):
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": [MATCHED]}}])
    ]

    response = await client.post(f"{JOBS}/find")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    [job] = response.json()["reply"]
    assert job["external_id"] == "jsearch-1"
    assert job["source"] == "JSearch"
    assert job["location"] == "Kuala Lumpur, Malaysia, remote"
    assert job["url"] == "https://jobs.example.com/1"
    assert job["status"] == "picked"
    assert job["analysis"] == {"fit": 67, "band": "possible", "requirements": READ_BACK}
    assert [j["id"] for j in (await client.get(JOBS)).json()["jobs"]] == [job["id"]]
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/find-jobs"
    message = a2a_sent(harness)[0]["params"]["message"]
    assert message["contextId"].startswith(f"{me['id']}:")
    assert message["parts"] == [{"data": {**agent_profile, "search": None}}]
    assert "metadata" not in a2a_sent(harness)[0]["params"]


async def test_the_search_sent_reaches_find_jobs(client, harness):
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    search = {"query": "Staff engineer", "location": "Remote", "posted_within": "week"}
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}]),
    ]

    await client.post(f"{JOBS}/find", json=search)
    await client.post(f"{JOBS}/find", json={"posted_within": "day"})

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


async def test_each_find_run_records_what_it_found(client, harness):
    strong = {
        **MATCHED,
        "posting": {**MATCHED["posting"], "id": "jsearch-2"},
        "fit": 70,
    }
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": [MATCHED]}}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": [MATCHED, strong]}}]),
    ]
    assert (await client.get(f"{JOBS}/runs/latest")).status_code == 404

    await client.post(f"{JOBS}/find")
    first = (await client.get(f"{JOBS}/runs/latest")).json()
    await client.post(f"{JOBS}/find")
    second = (await client.get(f"{JOBS}/runs/latest")).json()

    assert {k: first[k] for k in ("found", "new", "scored_70")} == {
        "found": 1,
        "new": 1,
        "scored_70": 0,
    }
    assert {k: second[k] for k in ("found", "new", "scored_70")} == {
        "found": 2,
        "new": 1,
        "scored_70": 1,
    }
    assert second["finished_at"] > first["finished_at"]


async def test_a_failed_find_run_records_no_counts(client, harness):
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": "JSearch is down"}])]

    await client.post(f"{JOBS}/find")

    assert (await client.get(f"{JOBS}/runs/latest")).status_code == 404


async def test_each_run_carries_the_users_model(client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})
    job = (
        await client.post(
            JOBS, json={"title": "Platform Engineer", "url": ANALYSIS["url"]}
        )
    ).json()
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"analysis": ANALYSIS}}]),
    ]

    await client.post(f"{JOBS}/find")
    await client.post(f"{JOBS}/{job['id']}/analyse")

    assert [sent["params"]["metadata"] for sent in a2a_sent(harness)] == [
        {"model": model}
    ] * 2


async def test_a_job_found_again_keeps_its_status(client, harness):
    found = {"jobs": [MATCHED]}
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": found}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": found}]),
    ]
    [job] = (await client.post(f"{JOBS}/find")).json()["reply"]
    await client.patch(f"{JOBS}/{job['id']}", json={"status": "dismissed"})

    again = await client.post(f"{JOBS}/find")

    assert [j["status"] for j in again.json()["reply"]] == ["dismissed"]
    assert len((await client.get(JOBS)).json()["jobs"]) == 1
    first, second = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert first["contextId"] != second["contextId"]


async def test_a_failed_search_returns_its_reason_and_stores_nothing(client, harness):
    reason = "JSearch did not answer"
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": reason}])]

    response = await client.post(f"{JOBS}/find")

    assert response.json() == {"status": "failed", "reason": reason}
    assert (await client.get(JOBS)).json()["jobs"] == []


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
    assert response.json() == {
        "status": "completed",
        "reply": {**job, "analysis": analysis},
    }
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

    assert response.json() == {"status": "failed", "reason": reason}
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
