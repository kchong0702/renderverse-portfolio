import pytest
from sqlalchemy.exc import IntegrityError

from src.core.auth.models import User
from src.core.config import get_settings
from src.features.preferences.models import JobPreferences
from tests.conftest import PREFIX
from tests.core.conftest import DATABASE_URL

PREFERENCES = f"{PREFIX}/preferences"


async def test_defaults_on_first_read(client):
    response = await client.get(PREFERENCES)

    assert response.status_code == 200
    assert response.json() == {
        "target_roles": "",
        "location": "",
        "countries": [],
        "visa_free_countries": [],
        "work_modes": [],
        "min_salary": None,
        "min_score": 70,
        "run_at": "08:00:00",
    }


async def test_patch_changes_only_the_fields_sent(client):
    await client.patch(
        PREFERENCES,
        json={
            "target_roles": "Backend engineer, Python",
            "min_salary": {"amount": 14000, "currency": "MYR", "period": "month"},
        },
    )

    response = await client.patch(
        PREFERENCES,
        json={
            "work_modes": ["hybrid", "remote"],
            "countries": ["MY", "SG"],
            "visa_free_countries": ["MY"],
            "min_score": 80,
            "run_at": "07:30",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "target_roles": "Backend engineer, Python",
        "location": "",
        "countries": ["MY", "SG"],
        "visa_free_countries": ["MY"],
        "work_modes": ["hybrid", "remote"],
        "min_salary": {"amount": 14000, "currency": "MYR", "period": "month"},
        "min_score": 80,
        "run_at": "07:30:00",
    }
    assert (await client.get(PREFERENCES)).json() == response.json()


async def test_a_null_salary_clears_it(client):
    await client.patch(
        PREFERENCES,
        json={"min_salary": {"amount": 14000, "currency": "MYR", "period": "month"}},
    )

    response = await client.patch(PREFERENCES, json={"min_salary": None})

    assert response.json()["min_salary"] is None


async def test_rejects_preferences_the_agents_cannot_read(client):
    for patch in (
        {"work_modes": ["office"]},
        {"countries": ["Malaysia"]},
        {"visa_free_countries": ["my"]},
        {"min_salary": {"amount": 0, "currency": "MYR", "period": "month"}},
        {"min_salary": {"amount": 100, "currency": "rm", "period": "month"}},
        {"min_score": 101},
    ):
        response = await client.patch(PREFERENCES, json=patch)
        assert response.status_code == 422, patch


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
@pytest.mark.parametrize(
    ("row", "check"),
    [
        ({"work_modes": ["remote", "office"]}, "ck_job_preferences_work_modes"),
        ({"min_salary_amount": 14000}, "ck_job_preferences_min_salary"),
        (
            {"min_salary_amount": 14000, "min_salary_currency": "MYR"},
            "ck_job_preferences_min_salary",
        ),
        ({"min_score": -1}, "ck_job_preferences_min_score"),
    ],
)
async def test_the_database_refuses_preferences_it_cannot_hold(
    postgres_app, row, check
):
    async with postgres_app.state.session_factory() as session:
        user = User(email=get_settings().auth.dev_email)
        session.add(user)
        await session.commit()
        session.add(JobPreferences(user_id=user.id, **row))

        with pytest.raises(IntegrityError, match=check):
            await session.commit()
