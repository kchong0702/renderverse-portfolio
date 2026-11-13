from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, inspect, select
from sqlalchemy.exc import IntegrityError

from src.core.auth.models import User
from src.features.applications.models import Application, ApplicationStep
from src.features.jobs.models import Job
from tests.conftest import PREFIX, _client
from tests.core.conftest import DATABASE_URL

APPLICATIONS = f"{PREFIX}/applications"

HARBOR = {
    "company": "Harbor Health",
    "role": "Software Engineer II",
    "stage": "applied",
    "applied_on": "2026-10-31",
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
    assert harbor == {**harbor, **HARBOR, "fit": None, "next_step": None, "overdue": []}
    draft = await client.post(
        APPLICATIONS, json={"company": "Kopi Cloud", "role": "Platform Engineer"}
    )
    assert draft.json()["stage"] == "draft"

    listed = await client.get(APPLICATIONS)
    assert [a["company"] for a in listed.json()] == ["Kopi Cloud", "Harbor Health"]

    replaced = await client.put(
        f"{APPLICATIONS}/{harbor['id']}",
        json={**HARBOR, "stage": "interview"},
    )
    assert replaced.status_code == 200
    assert replaced.json()["stage"] == "interview"
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


INTERVIEW = {
    "kind": "interview",
    "title": "Technical interview",
    "starts_at": "2030-11-11T10:00:00Z",
    "ends_at": "2030-11-11T11:00:00Z",
    "format": "video",
    "location": "https://meet.example/abc",
}


async def test_steps_add_list_reschedule_and_delete(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"

    added = await client.post(steps, json=INTERVIEW)
    take_home = await client.post(
        steps, json={"kind": "take_home", "title": "Take-home", "due_on": "2030-11-01"}
    )
    step = added.json()
    moved = await client.put(
        f"{steps}/{step['id']}",
        json={
            **INTERVIEW,
            "starts_at": "2030-11-12T10:00:00Z",
            "ends_at": "2030-11-12T11:00:00Z",
        },
    )
    deleted = await client.delete(f"{steps}/{take_home.json()['id']}")

    assert added.status_code == 201
    assert step == {
        **INTERVIEW,
        "id": step["id"],
        "application_id": harbor["id"],
        "email_thread_id": None,
        "due_on": None,
        "status": "open",
    }
    assert moved.json()["id"] == step["id"]
    assert moved.json()["starts_at"] == "2030-11-12T10:00:00Z"
    assert deleted.status_code == 204
    assert [s["id"] for s in (await client.get(steps)).json()] == [step["id"]]


async def test_steps_list_soonest_first(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"
    for title, when in (
        ("Onsite", {"starts_at": "2030-11-20T09:00:00Z"}),
        ("Take-home", {"due_on": "2030-11-15"}),
        ("Screen", {"starts_at": "2030-11-10T09:00:00Z"}),
    ):
        await client.post(steps, json={"kind": "interview", "title": title, **when})

    listed = await client.get(steps)

    assert [s["title"] for s in listed.json()] == ["Screen", "Take-home", "Onsite"]


async def test_a_step_needs_a_start_or_a_due_day(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"
    step = (await client.post(steps, json=INTERVIEW)).json()

    added = await client.post(steps, json={"kind": "follow_up", "title": "Nudge"})
    cleared = await client.put(
        f"{steps}/{step['id']}", json={**INTERVIEW, "starts_at": None}
    )

    assert added.status_code == 422
    assert cleared.status_code == 422
    assert (await client.get(steps)).json()[0]["starts_at"] is not None


async def test_a_step_needs_a_start_or_a_due_day_in_the_database(app, client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()

    with pytest.raises(IntegrityError):
        async with app.state.session_factory() as session, session.begin():
            session.add(
                ApplicationStep(
                    user_id=(
                        await session.get(Application, UUID(harbor["id"]))
                    ).user_id,
                    application_id=UUID(harbor["id"]),
                    kind="follow_up",
                    title="Nudge",
                )
            )


async def test_a_step_may_leave_its_title_to_its_kind(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()

    added = await client.post(
        f"{APPLICATIONS}/{harbor['id']}/steps",
        json={"kind": "follow_up", "due_on": "2030-11-01"},
    )

    assert added.status_code == 201
    assert added.json()["title"] == ""


async def test_a_step_time_needs_an_offset(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"

    naive = await client.post(
        steps, json={**INTERVIEW, "starts_at": "2030-11-11T10:00:00", "ends_at": None}
    )
    mixed = await client.post(
        steps, json={**INTERVIEW, "ends_at": "2030-11-11T11:00:00"}
    )

    assert (naive.status_code, mixed.status_code) == (422, 422)
    assert (await client.get(steps)).json() == []


async def test_a_step_ends_after_it_starts(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"

    unstarted = await client.post(
        steps, json={**INTERVIEW, "starts_at": None, "due_on": "2030-11-11"}
    )
    backwards = await client.post(
        steps, json={**INTERVIEW, "ends_at": "2030-11-11T09:00:00Z"}
    )

    assert unstarted.status_code == 422
    assert backwards.status_code == 422
    assert (await client.get(steps)).json() == []


async def test_a_step_ends_after_it_starts_in_the_database(app, client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()

    for when in (
        {"due_on": date(2030, 11, 11)},
        {"starts_at": datetime.fromisoformat("2030-11-11T12:00:00+00:00")},
    ):
        with pytest.raises(IntegrityError):
            async with app.state.session_factory() as session, session.begin():
                session.add(
                    ApplicationStep(
                        user_id=(
                            await session.get(Application, UUID(harbor["id"]))
                        ).user_id,
                        application_id=UUID(harbor["id"]),
                        kind="interview",
                        ends_at=datetime.fromisoformat("2030-11-11T11:00:00+00:00"),
                        **when,
                    )
                )


async def test_a_step_belongs_to_an_application_or_a_thread(app, client):
    await client.get(APPLICATIONS)

    with pytest.raises(IntegrityError):
        async with app.state.session_factory() as session, session.begin():
            user = await session.scalar(select(User))
            session.add(
                ApplicationStep(
                    user_id=user.id, kind="follow_up", due_on=date(2030, 11, 1)
                )
            )


async def test_the_next_step_is_the_soonest_open_step_still_ahead(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"
    for step in (
        {"title": "Past screen", "starts_at": "2020-11-10T09:00:00Z"},
        {"title": "Cancelled call", "starts_at": "2030-11-01T09:00:00Z"},
        {"title": "Done task", "due_on": "2030-11-02"},
        {"title": "Onsite", "starts_at": "2030-11-20T09:00:00Z"},
        {"title": "Take-home", "due_on": "2030-11-15"},
    ):
        await client.post(steps, json={"kind": "interview", **step})
    for step in (await client.get(steps)).json():
        status = {"Cancelled call": "cancelled", "Done task": "done"}.get(step["title"])
        if status:
            await client.put(
                f"{steps}/{step['id']}",
                json={**step, "status": status},
            )

    [listed] = (await client.get(APPLICATIONS)).json()

    assert listed["next_step"]["title"] == "Take-home"
    assert listed["overdue"] == []


async def test_open_steps_past_their_due_day_are_overdue(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"
    for title, status in (("Late take-home", "open"), ("Handed in", "done")):
        await client.post(
            steps,
            json={
                "kind": "take_home",
                "title": title,
                "due_on": "2020-11-15",
                "status": status,
            },
        )
    await client.post(
        steps,
        json={
            "kind": "follow_up",
            "title": "Called off",
            "due_on": "2020-11-16",
            "status": "cancelled",
        },
    )

    [listed] = (await client.get(APPLICATIONS)).json()

    assert [s["title"] for s in listed["overdue"]] == ["Late take-home"]
    assert listed["next_step"] is None


@pytest.mark.parametrize(
    ("timezone", "now", "overdue"),
    [
        ("Asia/Kuala_Lumpur", "2026-11-13T16:30:00+00:00", True),
        ("America/Bogota", "2026-11-14T03:00:00+00:00", False),
        (None, "2026-11-14T03:00:00+00:00", True),
    ],
)
async def test_due_days_end_at_midnight_in_the_users_zone(
    client, monkeypatch, timezone, now, overdue
):
    monkeypatch.setattr(
        "src.features.applications.service.utcnow",
        lambda: datetime.fromisoformat(now),
    )
    if timezone:
        await client.patch(
            f"{PREFIX}/settings", json={"scheduling": {"timezone": timezone}}
        )
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    await client.post(
        f"{APPLICATIONS}/{harbor['id']}/steps",
        json={"kind": "take_home", "title": "Take-home", "due_on": "2026-11-13"},
    )

    [listed] = (await client.get(APPLICATIONS)).json()

    assert [s["title"] for s in listed["overdue"]] == (["Take-home"] if overdue else [])
    assert (listed["next_step"] is None) is overdue


async def test_the_offer_deadline_is_the_open_offer_deadline_steps_day(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    steps = f"{APPLICATIONS}/{harbor['id']}/steps"
    offer = (
        await client.post(
            steps, json={"kind": "offer_deadline", "due_on": "2030-11-20"}
        )
    ).json()
    await client.post(steps, json=INTERVIEW)

    [listed] = (await client.get(APPLICATIONS)).json()
    await client.put(f"{steps}/{offer['id']}", json={**offer, "status": "done"})
    [decided] = (await client.get(APPLICATIONS)).json()

    assert listed["offer_deadline"] == "2030-11-20"
    assert listed["next_step"]["kind"] == "interview"
    assert decided["offer_deadline"] is None


async def test_applications_list_overdue_first_then_soonest_next_step_then_newest(
    client,
):
    names = ("Quiet old", "Overdue", "Soon", "Oldest overdue", "Quiet new")
    created = {
        name: (await client.post(APPLICATIONS, json={**HARBOR, "company": name})).json()
        for name in names
    }
    for name, day in (
        ("Overdue", "2020-11-15"),
        ("Soon", "2030-11-01"),
        ("Oldest overdue", "2020-11-10"),
    ):
        await client.post(
            f"{APPLICATIONS}/{created[name]['id']}/steps",
            json={"kind": "follow_up", "due_on": day},
        )

    listed = (await client.get(APPLICATIONS)).json()

    assert [a["company"] for a in listed] == [
        "Oldest overdue",
        "Overdue",
        "Soon",
        "Quiet new",
        "Quiet old",
    ]


async def test_applications_list_soonest_next_step_first(client):
    later, sooner, _ = [
        (await client.post(APPLICATIONS, json={**HARBOR, "company": c})).json()
        for c in ("Later", "Sooner", "None")
    ]
    for application, day in ((later, "2030-12-01"), (sooner, "2030-11-01")):
        await client.post(
            f"{APPLICATIONS}/{application['id']}/steps",
            json={"kind": "follow_up", "title": "Nudge", "due_on": day},
        )

    listed = (await client.get(APPLICATIONS)).json()

    assert [a["company"] for a in listed] == ["Sooner", "Later", "None"]


async def test_steps_in_a_range_include_past_ones_of_every_application(client):
    harbor, kopi = [
        (await client.post(APPLICATIONS, json={**HARBOR, "company": c})).json()
        for c in ("Harbor Health", "Kopi Cloud")
    ]
    for application, title, starts_at, status in (
        (harbor, "Screen", "2020-11-09T09:00:00Z", "done"),
        (kopi, "Onsite", "2020-11-13T09:00:00Z", "open"),
        (harbor, "Before", "2020-11-08T23:59:00Z", "open"),
        (kopi, "After", "2020-11-16T00:00:00Z", "open"),
    ):
        await client.post(
            f"{APPLICATIONS}/{application['id']}/steps",
            json={
                **INTERVIEW,
                "title": title,
                "starts_at": starts_at,
                "ends_at": None,
                "status": status,
            },
        )
    await client.post(
        f"{APPLICATIONS}/{harbor['id']}/steps",
        json={"kind": "take_home", "due_on": "2020-11-12"},
    )

    listed = await client.get(
        f"{APPLICATIONS}/steps",
        params={"start": "2020-11-09T00:00:00Z", "end": "2020-11-16T00:00:00Z"},
    )

    assert listed.status_code == 200
    assert [(s["title"], s["application_id"]) for s in listed.json()] == [
        ("Screen", harbor["id"]),
        ("Onsite", kopi["id"]),
    ]


async def test_steps_of_another_application_are_not_found(client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    kopi = (
        await client.post(APPLICATIONS, json={**HARBOR, "company": "Kopi Cloud"})
    ).json()
    step = (
        await client.post(f"{APPLICATIONS}/{harbor['id']}/steps", json=INTERVIEW)
    ).json()
    wrong = f"{APPLICATIONS}/{kopi['id']}/steps/{step['id']}"
    assert (await client.put(wrong, json=INTERVIEW)).status_code == 404
    assert (await client.delete(wrong)).status_code == 404
    missing = f"{APPLICATIONS}/{uuid4()}/steps"
    assert (await client.get(missing)).status_code == 404
    assert (await client.post(missing, json=INTERVIEW)).status_code == 404


async def test_steps_are_saved_and_deleted_by_id_for_their_user_only(app, client):
    harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
    step = (
        await client.post(f"{APPLICATIONS}/{harbor['id']}/steps", json=INTERVIEW)
    ).json()
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.flush()
        application = Application(
            user_id=other.id, job=Job(user_id=other.id, title="Their role")
        )
        session.add(application)
        await session.flush()
        theirs = ApplicationStep(
            user_id=other.id,
            application_id=application.id,
            kind="follow_up",
            due_on=date(2030, 11, 1),
        )
        session.add(theirs)
        await session.commit()

    done = await client.put(
        f"{APPLICATIONS}/steps/{step['id']}", json={**INTERVIEW, "status": "done"}
    )
    deleted = await client.delete(f"{APPLICATIONS}/steps/{step['id']}")
    put_theirs = await client.put(f"{APPLICATIONS}/steps/{theirs.id}", json=INTERVIEW)
    delete_theirs = await client.delete(f"{APPLICATIONS}/steps/{theirs.id}")

    assert done.json()["status"] == "done"
    assert deleted.status_code == 204
    assert (put_theirs.status_code, delete_theirs.status_code) == (404, 404)


async def test_steps_are_indexed_by_their_email_thread(app):
    async with app.state.session_factory.kw["bind"].connect() as connection:
        indexes = await connection.run_sync(
            lambda sync: inspect(sync).get_indexes("application_steps")
        )

    assert ["email_thread_id"] in [index["column_names"] for index in indexes]


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_deleting_an_application_deletes_its_steps(postgres_app):
    async with _client(postgres_app) as client:
        harbor = (await client.post(APPLICATIONS, json=HARBOR)).json()
        step = (
            await client.post(f"{APPLICATIONS}/{harbor['id']}/steps", json=INTERVIEW)
        ).json()

        await client.delete(f"{APPLICATIONS}/{harbor['id']}")

    async with postgres_app.state.session_factory() as session:
        assert await session.get(ApplicationStep, UUID(step["id"])) is None
