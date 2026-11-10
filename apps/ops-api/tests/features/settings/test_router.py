import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.auth.models import User
from src.core.config import get_settings
from src.features.settings.models import UserSettings
from tests.conftest import PREFIX, FakeArtifact, FakeGoogle, FakeHarness, _app, _client
from tests.core.conftest import DATABASE_URL


async def test_defaults_on_first_read(client):
    response = await client.get(f"{PREFIX}/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["job_agent"] == {
        "query": "",
        "location": "",
        "run_at": "08:00:00",
        "min_score": 70,
    }
    assert body["automation"] == {
        "tailor_strong_matches": True,
        "follow_up_reminders": True,
        "suggest_replies": True,
        "add_interview_invites": True,
        "offer_free_slots": True,
    }
    assert body["scheduling"] == {
        "work_day_start": "09:00:00",
        "work_day_end": "18:00:00",
        "meeting_gap_minutes": 30,
    }
    assert body["ai_model"] is None
    assert {c["id"]: c["status"] for c in body["connections"]} == {
        "google": "not_connected",
        "jsearch": "not_connected",
        "portfolio_site": "not_connected",
    }


async def test_patch_changes_only_the_fields_sent(client):
    response = await client.patch(
        f"{PREFIX}/settings",
        json={
            "job_agent": {"query": "Backend engineer, Python", "min_score": 80},
            "automation": {"suggest_replies": False, "offer_free_slots": False},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_agent"]["query"] == "Backend engineer, Python"
    assert body["job_agent"]["min_score"] == 80
    assert body["job_agent"]["run_at"] == "08:00:00"
    assert body["automation"]["suggest_replies"] is False
    assert body["automation"]["offer_free_slots"] is False
    assert body["automation"]["add_interview_invites"] is True
    assert body["automation"]["follow_up_reminders"] is True

    reread = await client.get(f"{PREFIX}/settings")
    assert reread.json() == body


async def test_work_day_must_end_after_it_starts(client):
    response = await client.patch(
        f"{PREFIX}/settings",
        json={"scheduling": {"work_day_start": "19:00", "work_day_end": "18:00"}},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The work day must end after it starts"


async def test_rows_record_who_created_and_changed_them(app, client):
    async with app.state.session_factory() as session:
        user = User(email=get_settings().auth.dev_email)
        session.add(user)
        await session.flush()
        session.add(UserSettings(user_id=user.id))
        await session.commit()

    await client.patch(f"{PREFIX}/settings", json={"job_agent": {"min_score": 80}})

    async with app.state.session_factory() as session:
        row = await session.get(UserSettings, user.id)
    assert row is not None
    assert row.created_by == "system"
    assert row.updated_by == f"user:{user.id}"


@pytest.fixture
async def postgres_app(
    harness: FakeHarness, artifact: FakeArtifact, google: FakeGoogle
) -> AsyncIterator[FastAPI]:
    """The app on the test Postgres database, its dev user deleted after the test"""
    engine = create_async_engine(DATABASE_URL)
    async for app in _app(harness, artifact, google, engine=engine):
        yield app
        async with app.state.session_factory() as session, session.begin():
            await session.execute(
                delete(User).where(User.email == get_settings().auth.dev_email)
            )


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_first_read_that_overlaps_another_gets_the_defaults(postgres_app):
    async with (
        postgres_app.state.session_factory() as other,
        _client(postgres_app) as client,
    ):
        user = User(email=get_settings().auth.dev_email)
        other.add(user)
        await other.commit()
        other.add(UserSettings(user_id=user.id))
        await other.flush()
        reading = asyncio.create_task(client.get(f"{PREFIX}/settings"))
        async with asyncio.timeout(5):
            while not await other.scalar(
                text("SELECT count(*) FROM pg_locks WHERE NOT granted")
            ):
                await asyncio.sleep(0.01)
        await other.commit()
        response = await reading

    assert response.status_code == 200
    assert response.json()["job_agent"]["min_score"] == 70
