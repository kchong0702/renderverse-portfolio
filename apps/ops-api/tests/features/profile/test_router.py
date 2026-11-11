import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.core.auth.models import User
from src.core.config import get_settings
from src.features.profile.enums import EntryKind
from src.features.profile.models import Profile, ProfileEntry
from tests.conftest import PREFIX, _client
from tests.core.conftest import DATABASE_URL

PROFILE = f"{PREFIX}/profile"

ACME = {
    "kind": "role",
    "title": "Senior Engineer",
    "organisation": "Acme Corp",
    "location": "Kuala Lumpur",
    "start": "2022-03",
    "end": "present",
    "highlights": ["Led the migration of 30 services to Kubernetes."],
}


async def test_profile_starts_empty(client):
    response = await client.get(PROFILE)

    assert response.status_code == 200
    assert response.json() == {
        "name": "",
        "headline": "",
        "location": "",
        "email": "",
        "phone": "",
        "links": [],
        "summary": "",
        "preferences": {
            "work_modes": [],
            "countries": [],
            "authorised_countries": [],
            "min_salary": None,
        },
    }


async def test_patch_changes_only_the_fields_sent(client):
    await client.patch(PROFILE, json={"name": "Kelvin Chong", "location": "KL"})
    preferences = {
        "work_modes": ["hybrid", "remote"],
        "countries": ["MY", "SG"],
        "authorised_countries": ["MY"],
        "min_salary": {"amount": 14000, "currency": "MYR", "period": "month"},
    }

    response = await client.patch(
        PROFILE, json={"headline": "Backend engineer", "preferences": preferences}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Kelvin Chong"
    assert body["location"] == "KL"
    assert body["headline"] == "Backend engineer"
    assert body["preferences"] == preferences
    assert (await client.get(PROFILE)).json() == body


async def test_rejects_preferences_the_agents_cannot_read(client):
    for preferences in (
        {"work_modes": ["office"]},
        {"countries": ["Malaysia"]},
        {"min_salary": {"amount": 0, "currency": "MYR", "period": "month"}},
        {"min_salary": {"amount": 100, "currency": "rm", "period": "month"}},
    ):
        response = await client.patch(PROFILE, json={"preferences": preferences})
        assert response.status_code == 422, preferences


async def test_entries_add_list_replace_and_delete(client):
    created = await client.post(f"{PROFILE}/entries", json=ACME)
    assert created.status_code == 201
    entry = created.json()
    project = await client.post(
        f"{PROFILE}/entries",
        json={"kind": "project", "title": "Renderverse", "start": "2025-01"},
    )

    listed = await client.get(f"{PROFILE}/entries")
    assert [e["title"] for e in listed.json()] == ["Senior Engineer", "Renderverse"]

    replaced = await client.put(
        f"{PROFILE}/entries/{entry['id']}",
        json={**ACME, "end": "2024-12", "archived": True},
    )
    assert replaced.status_code == 200
    assert replaced.json()["end"] == "2024-12"
    assert replaced.json()["archived"] is True
    assert replaced.json()["kind"] == "role"

    deleted = await client.delete(f"{PROFILE}/entries/{project.json()['id']}")
    assert deleted.status_code == 204
    assert [e["id"] for e in (await client.get(f"{PROFILE}/entries")).json()] == [
        entry["id"]
    ]


async def test_entry_end_cannot_be_before_start(client):
    response = await client.post(
        f"{PROFILE}/entries", json={**ACME, "start": "2022-03", "end": "2021-12"}
    )

    assert response.status_code == 422


async def test_entries_of_another_user_are_not_found(app, client):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.commit()

    async with app.state.session_factory() as session:
        theirs = ProfileEntry(user_id=other.id, kind=EntryKind.ROLE, title="Their job")
        session.add(theirs)
        await session.commit()

    assert (await client.get(f"{PROFILE}/entries")).json() == []
    put = await client.put(f"{PROFILE}/entries/{theirs.id}", json={"title": "Mine"})
    assert put.status_code == 404
    assert (await client.delete(f"{PROFILE}/entries/{theirs.id}")).status_code == 404
    assert (await client.delete(f"{PROFILE}/skills/{uuid4()}")).status_code == 404


async def test_skills_add_replace_and_delete(client):
    created = await client.post(
        f"{PROFILE}/skills", json={"name": "Python", "group": "Languages"}
    )
    assert created.status_code == 201
    skill = created.json()

    replaced = await client.put(
        f"{PROFILE}/skills/{skill['id']}",
        json={"name": "Python", "group": "Languages", "archived": True},
    )
    assert replaced.json()["archived"] is True

    assert (await client.delete(f"{PROFILE}/skills/{skill['id']}")).status_code == 204
    assert (await client.get(f"{PROFILE}/skills")).json() == []


async def test_agent_profile_has_the_harness_shape(client):
    await client.patch(
        PROFILE,
        json={"preferences": {"work_modes": ["remote"], "countries": ["MY"]}},
    )
    role = (await client.post(f"{PROFILE}/entries", json=ACME)).json()
    degree = (
        await client.post(
            f"{PROFILE}/entries",
            json={
                "kind": "education",
                "title": "BSc Computer Science",
                "organisation": "University of Malaya",
                "start": "2013-09",
                "end": "2017-06",
            },
        )
    ).json()
    await client.post(
        f"{PROFILE}/entries",
        json={"kind": "project", "title": "Capstone", "archived": True},
    )
    skill = (
        await client.post(
            f"{PROFILE}/skills", json={"name": "Kubernetes", "group": "Platform"}
        )
    ).json()
    await client.post(f"{PROFILE}/skills", json={"name": "Perl", "archived": True})

    response = await client.get(f"{PROFILE}/agent")

    assert response.status_code == 200
    assert response.json() == {
        "facts": [
            {
                "id": f"role-{role['id']}",
                "text": "Senior Engineer at Acme Corp, Kuala Lumpur\n"
                "Led the migration of 30 services to Kubernetes.",
                "start": "2022-03",
                "end": "present",
            },
            {
                "id": f"education-{degree['id']}",
                "text": "BSc Computer Science, University of Malaya (2013 to 2017)",
                "start": None,
                "end": None,
            },
            {
                "id": f"skill-{skill['id']}",
                "text": "Platform: Kubernetes",
                "start": None,
                "end": None,
            },
        ],
        "preferences": {
            "work_modes": ["remote"],
            "countries": ["MY"],
            "authorised_countries": [],
            "min_salary": None,
        },
    }


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_first_read_that_overlaps_another_gets_the_profile(postgres_app):
    async with (
        postgres_app.state.session_factory() as other,
        _client(postgres_app) as client,
    ):
        user = User(email=get_settings().auth.dev_email)
        other.add(user)
        await other.commit()
        other.add(Profile(user_id=user.id, name="Kelvin Chong"))
        await other.flush()
        reading = asyncio.create_task(client.get(PROFILE))
        async with asyncio.timeout(5):
            while not await other.scalar(
                text("SELECT count(*) FROM pg_locks WHERE NOT granted")
            ):
                await asyncio.sleep(0.01)
        await other.commit()
        response = await reading

    assert response.status_code == 200
    assert response.json()["name"] == "Kelvin Chong"


async def test_entries_stay_off_the_site_until_turned_on(client):
    created = await client.post(
        f"{PROFILE}/entries", json={"kind": "project", "title": "Renderverse"}
    )
    assert created.json()["on_site"] is False

    replaced = await client.put(
        f"{PROFILE}/entries/{created.json()['id']}",
        json={"title": "Renderverse", "on_site": True},
    )

    assert replaced.json()["on_site"] is True
    assert (await client.get(f"{PROFILE}/entries")).json()[0]["on_site"] is True
