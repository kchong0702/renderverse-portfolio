from uuid import uuid4

from src.core.auth.models import User
from src.features.jobs.models import Job
from tests.conftest import PREFIX

JOBS = f"{PREFIX}/jobs"

ANALYSIS = {
    "fit": 86,
    "requirements": [
        {
            "text": "5+ years building backend services",
            "match": "met",
            "reason": "About 7 years across 3 roles",
        },
        {
            "text": "Kafka or another event bus",
            "importance": "nice_to_have",
            "match": "partly",
            "reason": "In skills, not linked to a role",
        },
        {"text": "Conversational Bahasa Malaysia", "match": "not_met"},
    ],
}

NORTHWIND = {
    "external_id": "jsearch-1",
    "source": "JSearch",
    "title": "Senior Backend Engineer",
    "company": "Northwind Labs",
    "location": "Kuala Lumpur, hybrid",
    "salary": "MYR 14,000 to 18,000 a month",
    "url": "https://jobs.example.com/1",
    "posted_at": "2026-11-07T09:00:00Z",
    "analysis": ANALYSIS,
}


async def test_jobs_start_empty(client):
    response = await client.get(JOBS)

    assert response.status_code == 200
    assert response.json() == []


async def test_added_job_keeps_its_analysis_with_the_band(client):
    created = await client.post(JOBS, json=NORTHWIND)

    assert created.status_code == 201
    job = created.json()
    assert job["status"] == "picked"
    assert job["analysis"] == {
        "fit": 86,
        "band": "excellent",
        "requirements": [
            {**ANALYSIS["requirements"][0], "importance": "required"},
            ANALYSIS["requirements"][1],
            {**ANALYSIS["requirements"][2], "importance": "required", "reason": ""},
        ],
    }
    assert (await client.get(JOBS)).json()[0]["analysis"] == job["analysis"]


async def test_jobs_list_best_fit_first_and_unanalysed_last(client):
    await client.post(JOBS, json={"title": "Not analysed yet"})
    for fit in (58, 78):
        await client.post(
            JOBS, json={"title": f"Fit {fit}", "analysis": {**ANALYSIS, "fit": fit}}
        )

    jobs = (await client.get(JOBS)).json()

    assert [j["title"] for j in jobs] == ["Fit 78", "Fit 58", "Not analysed yet"]
    assert [j["analysis"] and j["analysis"]["band"] for j in jobs] == [
        "good",
        "possible",
        None,
    ]


async def test_adding_a_job_again_refreshes_it_and_keeps_its_status(client):
    job = (await client.post(JOBS, json=NORTHWIND)).json()
    await client.patch(f"{JOBS}/{job['id']}", json={"status": "saved"})

    again = await client.post(
        JOBS, json={**NORTHWIND, "title": "Lead Backend Engineer", "analysis": None}
    )

    assert again.json()["id"] == job["id"]
    assert again.json()["status"] == "saved"
    assert again.json()["analysis"] is None
    assert [j["title"] for j in (await client.get(JOBS)).json()] == [
        "Lead Backend Engineer"
    ]


async def test_save_and_dismiss_a_job(client):
    job = (await client.post(JOBS, json=NORTHWIND)).json()

    saved = await client.patch(f"{JOBS}/{job['id']}", json={"status": "saved"})
    dismissed = await client.patch(f"{JOBS}/{job['id']}", json={"status": "dismissed"})

    assert saved.json()["status"] == "saved"
    assert dismissed.json()["status"] == "dismissed"
    assert (await client.get(JOBS)).json()[0]["status"] == "dismissed"


async def test_replace_analysis(client):
    job = (await client.post(JOBS, json={"title": "Platform Engineer"})).json()

    response = await client.put(
        f"{JOBS}/{job['id']}/analysis",
        json={
            "fit": 49,
            "requirements": [{"text": "Terraform", "match": "not_met"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["analysis"]["band"] == "poor"
    assert (await client.get(JOBS)).json()[0]["analysis"]["fit"] == 49


async def test_rejects_analyses_the_screen_cannot_show(client):
    job = (await client.post(JOBS, json={"title": "Platform Engineer"})).json()

    for analysis in (
        {**ANALYSIS, "fit": 101},
        {**ANALYSIS, "requirements": []},
        {**ANALYSIS, "requirements": [{"text": "Terraform", "match": "covered"}]},
    ):
        response = await client.put(f"{JOBS}/{job['id']}/analysis", json=analysis)
        assert response.status_code == 422, analysis


async def test_jobs_of_another_user_are_not_found(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()

    async with app.state.session_factory() as session:
        theirs = Job(user_id=other.id, title="Their job", external_id="jsearch-1")
        session.add(theirs)
        await session.commit()

    assert (await client.get(JOBS)).json() == []
    patch = await client.patch(f"{JOBS}/{theirs.id}", json={"status": "saved"})
    assert patch.status_code == 404
    put = await client.put(f"{JOBS}/{uuid4()}/analysis", json=ANALYSIS)
    assert put.status_code == 404
    mine = await client.post(JOBS, json=NORTHWIND)
    assert mine.json()["id"] != str(theirs.id)
