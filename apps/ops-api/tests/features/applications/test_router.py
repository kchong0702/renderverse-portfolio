from uuid import uuid4

import pytest
from sqlalchemy import event

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


async def _job(client, **fields) -> dict:
    """Store a posting and return it"""
    response = await client.post(
        f"{PREFIX}/jobs",
        json={
            "title": "Senior Backend Engineer",
            "company": "Northwind Labs",
            **fields,
        },
    )
    return response.json()


async def test_applications_start_empty(client):
    response = await client.get(APPLICATIONS)

    assert response.status_code == 200
    assert response.json() == []


async def test_applications_add_list_replace_and_delete(client):
    created = await client.post(APPLICATIONS, json=HARBOR)
    assert created.status_code == 201
    harbor = created.json()
    assert harbor == {**harbor, **HARBOR, "fit": None}
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
    assert replaced.json()["company"] == "Harbor Health"

    deleted = await client.delete(f"{APPLICATIONS}/{draft.json()['id']}")
    assert deleted.status_code == 204
    assert [a["id"] for a in (await client.get(APPLICATIONS)).json()] == [harbor["id"]]


async def test_a_manual_application_saves_its_job(client):
    created = await client.post(
        APPLICATIONS,
        json={
            **HARBOR,
            "url": "https://harbor.example/careers/1",
            "location": "Kuala Lumpur",
        },
    )

    [job] = (await client.get(f"{PREFIX}/jobs")).json()["jobs"]
    assert created.json()["job_id"] == job["id"]
    assert created.json()["by_hand"] is True
    assert {k: job[k] for k in ("source", "status", "title", "company", "url")} == {
        "source": "manual",
        "status": "saved",
        "title": "Software Engineer II",
        "company": "Harbor Health",
        "url": "https://harbor.example/careers/1",
    }
    assert job["location"] == "Kuala Lumpur"


async def test_editing_an_application_renames_its_job(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()

    replaced = await client.put(
        f"{APPLICATIONS}/{harbor['id']}",
        json={**HARBOR, "company": "Harbor Group", "role": "Staff Engineer"},
    )

    [job] = (await client.get(f"{PREFIX}/jobs")).json()["jobs"]
    assert (replaced.json()["company"], replaced.json()["role"]) == (
        "Harbor Group",
        "Staff Engineer",
    )
    assert (job["company"], job["title"]) == ("Harbor Group", "Staff Engineer")


async def test_a_found_jobs_company_and_role_cannot_be_edited(client):
    job = await _job(client, external_id="js-1", source="JSearch")
    created = (await client.post(APPLICATIONS, json={"job_id": job["id"]})).json()
    url = f"{APPLICATIONS}/{created['id']}"

    renamed = await client.put(
        url, json={"stage": "applied", "company": "Acme", "role": "Staff Engineer"}
    )
    staged = await client.put(url, json={"stage": "applied"})
    await _job(client, external_id="js-1", source="JSearch")

    assert created["by_hand"] is False
    assert renamed.status_code == 422
    assert staged.status_code == 200
    [listed] = (await client.get(APPLICATIONS)).json()
    assert (listed["stage"], listed["company"], listed["role"]) == (
        "applied",
        "Northwind Labs",
        "Senior Backend Engineer",
    )


async def test_listing_applications_reads_their_jobs_through_the_join(app, client):
    await client.post(APPLICATIONS, json=HARBOR)
    await _job(client)
    statements: list[str] = []
    engine = app.state.session_factory.kw["bind"].sync_engine

    def record(_connection, _cursor, statement, *_):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        listed = await client.get(APPLICATIONS)
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert [a["company"] for a in listed.json()] == ["Harbor Health"]
    assert not [s for s in statements if "FROM jobs" in s]


async def test_deleting_a_hand_tracked_application_deletes_its_job(client):
    manual = (await client.post(APPLICATIONS, json=HARBOR)).json()
    stored = await _job(client)
    linked = (await client.post(APPLICATIONS, json={"job_id": stored["id"]})).json()

    for application in (manual, linked):
        await client.delete(f"{APPLICATIONS}/{application['id']}")

    jobs = (await client.get(f"{PREFIX}/jobs")).json()["jobs"]
    assert [job["id"] for job in jobs] == [stored["id"]]


async def test_a_manual_application_that_fails_leaves_no_job(client):
    def refuse(*_):
        raise RuntimeError("insert refused")

    event.listen(Application, "before_insert", refuse)
    try:
        with pytest.raises(RuntimeError):
            await client.post(APPLICATIONS, json=HARBOR)
    finally:
        event.remove(Application, "before_insert", refuse)

    assert (await client.get(f"{PREFIX}/jobs")).json()["jobs"] == []


async def test_application_for_a_job_takes_the_jobs_company_role_and_fit(client):
    job = await _job(
        client,
        analysis={"fit": 86, "requirements": [{"text": "Python", "match": "met"}]},
    )

    created = await client.post(APPLICATIONS, json={"job_id": job["id"]})
    await client.put(
        f"{PREFIX}/jobs/{job['id']}/analysis",
        json={"fit": 71, "requirements": [{"text": "Python", "match": "partly"}]},
    )

    assert created.status_code == 201
    assert created.json()["fit"] == 86
    assert created.json()["job_id"] == job["id"]
    assert created.json()["company"] == "Northwind Labs"
    assert created.json()["role"] == "Senior Backend Engineer"
    assert (await client.get(APPLICATIONS)).json()[0]["fit"] == 71


async def test_a_job_takes_one_application(client):
    job = await _job(client)

    first = await client.post(APPLICATIONS, json={"job_id": job["id"]})
    second = await client.post(APPLICATIONS, json={"job_id": job["id"]})

    assert first.status_code == 201
    assert second.status_code == 409
    assert len((await client.get(APPLICATIONS)).json()) == 1


async def test_an_application_names_a_job_or_a_company_and_role(client):
    job = await _job(client)

    both = await client.post(APPLICATIONS, json={**HARBOR, "job_id": job["id"]})
    neither = await client.post(APPLICATIONS, json={"stage": "applied"})

    assert both.status_code == 422
    assert neither.status_code == 422


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
        response = await client.post(APPLICATIONS, json={"job_id": str(job_id)})
        assert response.status_code == 404
        assert response.json()["detail"] == "No such job"


async def test_applications_of_another_user_are_not_found(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()

    async with app.state.session_factory() as session:
        theirs = Application(
            user_id=other.id, job=Job(user_id=other.id, title="Their role")
        )
        session.add(theirs)
        await session.commit()

    assert (await client.get(APPLICATIONS)).json() == []
    put = await client.put(f"{APPLICATIONS}/{theirs.id}", json=HARBOR)
    assert put.status_code == 404
    assert (await client.delete(f"{APPLICATIONS}/{theirs.id}")).status_code == 404
