import pytest
from sqlalchemy import text

from src.core.auth.models import User
from src.core.config import get_settings
from src.core.providers import Provider
from src.features.connections import (
    ConnectionService,
    GoogleDetails,
    JSearchDetails,
)
from tests.core.conftest import DATABASE_URL


def _service(session, provider: Provider) -> ConnectionService:
    """The connection service for the provider, keyed as the server is"""
    key = {
        Provider.GOOGLE: get_settings().google.encryption_key,
        Provider.JSEARCH: get_settings().jsearch.encryption_key,
    }[provider]
    return ConnectionService(session, provider, key, provider.name, "Unreadable")


async def test_a_google_connection_is_set_read_replaced_and_deleted(app):
    async with app.state.session_factory() as session:
        user = User(email="someone@example.com")
        session.add(user)
        await session.flush()
        service = _service(session, Provider.GOOGLE)

        await service.connect(
            user.id, "secret-1", account="a@example.com", scopes=["a"]
        )
        first = await service.get(user.id)
        assert first is not None
        assert (first.account, first.details, service.secret(first)) == (
            "a@example.com",
            GoogleDetails(scopes=["a"]),
            "secret-1",
        )

        await service.connect(user.id, "secret-2")
        second = await service.get(user.id)
        assert second is not None
        assert (second.account, second.details, service.secret(second)) == (
            "",
            GoogleDetails(scopes=[]),
            "secret-2",
        )

        await service.disconnect(user.id)
        assert await service.get(user.id) is None
        await service.disconnect(user.id)


async def test_a_jsearch_quota_is_recorded_and_cleared_when_the_key_is_replaced(app):
    async with app.state.session_factory() as session:
        user = User(email="someone@example.com")
        session.add(user)
        await session.flush()
        service = _service(session, Provider.JSEARCH)

        await service.connect(user.id, "secret-1")
        await service.record_quota(user.id, 9, 10)
        first = await service.get(user.id)
        assert first is not None
        assert (first.details, service.secret(first)) == (
            JSearchDetails(quota_remaining=9, quota_limit=10),
            "secret-1",
        )

        await service.connect(user.id, "secret-2")
        second = await service.get(user.id)
        assert second is not None
        assert (second.details, service.secret(second)) == (
            JSearchDetails(),
            "secret-2",
        )

        await service.disconnect(user.id)
        assert await service.get(user.id) is None
        await service.disconnect(user.id)


async def test_a_quota_recorded_after_the_connection_is_gone_is_dropped(app):
    async with app.state.session_factory() as session, session.begin():
        user = User(email="someone@example.com")
        session.add(user)
        await session.flush()
        await _service(session, Provider.JSEARCH).connect(user.id, "secret")

    async with app.state.session_factory() as run:
        service = _service(run, Provider.JSEARCH)
        loaded = await service.get(user.id)
        assert loaded is not None
        async with app.state.session_factory() as settings, settings.begin():
            await _service(settings, Provider.JSEARCH).disconnect(user.id)

        await service.record_quota(user.id, 9, 10)
        await run.commit()

    async with app.state.session_factory() as session:
        assert await _service(session, Provider.JSEARCH).get(user.id) is None


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_recorded_quota_is_merged_into_the_stored_details(postgres_app):
    async with postgres_app.state.session_factory() as session, session.begin():
        user = User(email=get_settings().auth.dev_email)
        session.add(user)
        await session.flush()
        service = _service(session, Provider.JSEARCH)
        await service.connect(user.id, "secret")
        await service.record_quota(user.id, 9, 10)

    async with postgres_app.state.session_factory() as session:
        stored = (
            await session.execute(
                text(
                    "SELECT pg_typeof(details)::text, details FROM connections "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": user.id},
            )
        ).one()
    assert tuple(stored) == (
        "jsonb",
        {"provider": "jsearch", "quota_remaining": 9, "quota_limit": 10},
    )
