import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from src.core.auth.models import User
from src.core.config import get_settings
from src.db.base import as_utc
from src.features.profile.enums import EntryKind
from src.features.profile.models import Profile, ProfileEntry, ProfileProject
from src.features.profile.schemas import ProfileLink
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
    }


async def test_patch_changes_only_the_fields_sent(client):
    await client.patch(PROFILE, json={"name": "Kelvin Chong", "location": "KL"})

    response = await client.patch(PROFILE, json={"headline": "Backend engineer"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Kelvin Chong"
    assert body["location"] == "KL"
    assert body["headline"] == "Backend engineer"
    assert (await client.get(PROFILE)).json() == body


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
        f"{PREFIX}/preferences",
        json={
            "work_modes": ["remote"],
            "countries": ["MY"],
            "visa_free_countries": ["SG"],
        },
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
            "authorised_countries": ["SG"],
            "min_salary": None,
        },
    }


async def test_links_are_labelled_and_at_most_three(client):
    links = [
        {"label": "Website", "url": "https://kelvinchong.dev"},
        {"label": "LinkedIn", "url": "https://www.linkedin.com/in/kelvin"},
        {"label": "GitHub", "url": "https://github.com/kchong0702"},
    ]

    saved = await client.patch(PROFILE, json={"links": links})
    too_many = await client.patch(
        PROFILE, json={"links": [*links, {"label": "X", "url": "https://x.com/k"}]}
    )
    unlabelled = await client.patch(
        PROFILE, json={"links": [{"url": "https://kelvinchong.dev"}]}
    )

    assert saved.status_code == 200
    assert saved.json()["links"] == links
    assert too_many.status_code == 422
    assert unlabelled.status_code == 422
    assert (await client.get(PROFILE)).json()["links"] == links


async def test_a_projects_tools_and_links_reach_the_agents(client):
    project = (
        await client.post(
            f"{PROFILE}/entries",
            json={
                "kind": "project",
                "title": "Renderverse",
                "summary": "3D portfolio you can walk through",
                "link": "https://kelvinchong.dev",
                "code_link": "https://github.com/kchong0702/renderverse-portfolio",
                "tools": ["React", "Three.js"],
            },
        )
    ).json()

    assert project["tools"] == ["React", "Three.js"]
    assert project["link"] == "https://kelvinchong.dev"
    [fact] = (await client.get(f"{PROFILE}/agent")).json()["facts"]
    assert fact["text"] == (
        "Project Renderverse\n"
        "3D portfolio you can walk through\n"
        "Tools: React, Three.js\n"
        "Live at https://kelvinchong.dev\n"
        "Code at https://github.com/kchong0702/renderverse-portfolio"
    )


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


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_the_database_refuses_a_fourth_link(postgres_app):
    async with postgres_app.state.session_factory() as session:
        user = User(email=get_settings().auth.dev_email)
        session.add(user)
        await session.commit()
        session.add(
            Profile(
                user_id=user.id,
                links=[
                    ProfileLink(label=f"Link {n}", url=f"https://example.com/{n}")
                    for n in range(4)
                ],
            )
        )

        with pytest.raises(IntegrityError, match="ck_profiles_links"):
            await session.commit()


async def test_a_project_row_lives_and_dies_with_its_entry(app, client):
    async def projects() -> list[tuple]:
        async with app.state.session_factory() as session:
            return list(
                (
                    await session.execute(
                        select(ProfileProject.entry_id, ProfileProject.link)
                    )
                ).all()
            )

    project = {"kind": "project", "title": "Renderverse", "tools": ["React"]}
    created = (
        await client.post(
            f"{PROFILE}/entries", json={**project, "link": "https://a.example"}
        )
    ).json()
    assert await projects() == [(UUID(created["id"]), "https://a.example")]

    replaced = await client.put(
        f"{PROFILE}/entries/{created['id']}",
        json={**project, "link": "https://b.example", "on_site": True},
    )
    assert replaced.json()["link"] == "https://b.example"
    assert replaced.json()["on_site"] is True
    assert await projects() == [(UUID(created["id"]), "https://b.example")]

    await client.delete(f"{PROFILE}/entries/{created['id']}")
    assert await projects() == []


async def test_changing_only_a_projects_fields_updates_its_entry(app, client):
    async with app.state.session_factory() as session:
        user = User(email=get_settings().auth.dev_email)
        session.add(user)
        await session.flush()
        project = ProfileProject(user_id=user.id, kind=EntryKind.PROJECT, title="R")
        session.add(project)
        await session.commit()
        stamped = project.updated_at

    await client.put(
        f"{PROFILE}/entries/{project.id}", json={"title": "R", "on_site": True}
    )

    async with app.state.session_factory() as session:
        row = await session.get_one(ProfileProject, project.id)
    assert row.on_site is True
    assert row.created_by == "system"
    assert row.updated_by == f"user:{user.id}"
    assert as_utc(row.updated_at) > stamped


async def test_only_a_project_takes_project_fields(client):
    refusal = "Only a project has a link, code link, tools or a place on the site"
    project_fields = [
        {"link": "https://acme.example"},
        {"code_link": "https://github.com/acme/api"},
        {"tools": ["Go"]},
        {"on_site": True},
    ]
    role = await client.post(
        f"{PROFILE}/entries",
        json={**ACME, "link": None, "code_link": None, "tools": [], "on_site": False},
    )
    assert role.status_code == 201

    for fields in project_fields:
        added = await client.post(f"{PROFILE}/entries", json={**ACME, **fields})
        replaced = await client.put(
            f"{PROFILE}/entries/{role.json()['id']}", json={**ACME, **fields}
        )

        assert (added.status_code, added.json()["detail"]) == (422, refusal)
        assert (replaced.status_code, replaced.json()["detail"]) == (422, refusal)
    assert (await client.get(f"{PROFILE}/entries")).json() == [role.json()]


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
