from uuid import uuid4

from src.core.auth.models import User
from src.features.applications.models import Application
from src.features.jobs.models import Job
from tests.conftest import PREFIX

APPLICATIONS = f"{PREFIX}/applications"

HARBOR = {
    "company": "Harbor Health",
    "role": "Software Engineer II",
    "stage": "applied",
    "applied_on": "2026-10-31",
    "next_step": "Follow up",
    "next_step_at": "2026-11-09T09:00:00Z",
}


async def test_applications_start_empty(client):
    response = await client.get(APPLICATIONS)

    assert response.status_code == 200
    assert response.json() == []


async def test_applications_add_list_replace_and_delete(client):
    created = await client.post(APPLICATIONS, json=HARBOR)
    assert created.status_code == 201
    harbor = created.json()
    assert harbor == {**harbor, **HARBOR, "job_id": None, "fit": None}
    draft = await client.post(
        APPLICATIONS, json={"company": "Kopi Cloud", "role": "Platform Engineer"}
    )
    assert draft.json()["stage"] == "draft"

    listed = await client.get(APPLICATIONS)
    assert [a["company"] for a in listed.json()] == ["Harbor Health", "Kopi Cloud"]

    replaced = await client.put(
        f"{APPLICATIONS}/{harbor['id']}",
        json={
            **HARBOR,
            "stage": "interview",
            "next_step": "Technical interview",
            "next_step_at": "2026-11-11T10:00:00Z",
        },
    )
    assert replaced.status_code == 200
    assert replaced.json()["stage"] == "interview"
    assert replaced.json()["next_step"] == "Technical interview"

    deleted = await client.delete(f"{APPLICATIONS}/{draft.json()['id']}")
    assert deleted.status_code == 204
    assert [a["id"] for a in (await client.get(APPLICATIONS)).json()] == [harbor["id"]]


async def test_a_next_step_keeps_its_due_day_format_and_location(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    details = {
        "next_step_due": "2026-11-14",
        "next_step_format": "on_site",
        "next_step_location": "Level 12, Menara Harbor, Kuala Lumpur",
    }
    assert {key: harbor[key] for key in details} == dict.fromkeys(details)
    interview = {**HARBOR, "next_step": "Onsite loop", **details}

    replaced = await client.put(f"{APPLICATIONS}/{harbor['id']}", json=interview)

    assert replaced.json() == {**replaced.json(), **interview}
    [listed] = (await client.get(APPLICATIONS)).json()
    assert {key: listed[key] for key in details} == details
    cleared = await client.put(f"{APPLICATIONS}/{harbor['id']}", json=HARBOR)
    assert cleared.json()["next_step_format"] is None
    refused = await client.put(
        f"{APPLICATIONS}/{harbor['id']}",
        json={**interview, "next_step_format": "carrier_pigeon"},
    )
    assert refused.status_code == 422


async def test_application_for_a_job_takes_the_jobs_fit(client):
    job = (
        await client.post(
            f"{PREFIX}/jobs",
            json={
                "title": "Senior Backend Engineer",
                "company": "Northwind Labs",
                "analysis": {
                    "fit": 86,
                    "requirements": [{"text": "Python", "match": "met"}],
                },
            },
        )
    ).json()

    created = await client.post(
        APPLICATIONS,
        json={"job_id": job["id"], "company": "Northwind Labs", "role": job["title"]},
    )
    await client.put(
        f"{PREFIX}/jobs/{job['id']}/analysis",
        json={"fit": 71, "requirements": [{"text": "Python", "match": "partly"}]},
    )

    assert created.json()["fit"] == 86
    assert created.json()["job_id"] == job["id"]
    assert (await client.get(APPLICATIONS)).json()[0]["fit"] == 71


async def test_rejects_a_job_that_is_not_the_users(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()

    async with app.state.session_factory() as session:
        theirs = Job(user_id=other.id, title="Their job")
        session.add(theirs)
        await session.commit()

    for job_id in (theirs.id, uuid4()):
        response = await client.post(
            APPLICATIONS, json={**HARBOR, "job_id": str(job_id)}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "No such job"


async def test_applications_of_another_user_are_not_found(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()

    async with app.state.session_factory() as session:
        theirs = Application(user_id=other.id, company="Theirs", role="Their role")
        session.add(theirs)
        await session.commit()

    assert (await client.get(APPLICATIONS)).json() == []
    put = await client.put(f"{APPLICATIONS}/{theirs.id}", json=HARBOR)
    assert put.status_code == 404
    assert (await client.delete(f"{APPLICATIONS}/{theirs.id}")).status_code == 404
