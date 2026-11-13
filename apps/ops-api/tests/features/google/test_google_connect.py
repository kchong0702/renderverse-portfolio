from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, text, update

from src.core.auth.dependencies import current_user
from src.core.auth.models import User
from src.core.config import reload_settings
from src.core.providers import Provider
from src.features.connections import Connection, GoogleDetails
from tests.conftest import (
    ENCRYPTION_KEY,
    GOOGLE_SCOPES,
    PREFIX,
    _client,
    connect_google,
)
from tests.core.conftest import DATABASE_URL

CONNECT = f"{PREFIX}/integrations/google/connect"
CALLBACK = f"{PREFIX}/integrations/google/callback"


async def _accounts(app) -> list[Connection]:
    """Every stored Google connection"""
    async with app.state.session_factory() as session:
        return list(
            (
                await session.scalars(
                    select(Connection).where(Connection.provider == Provider.GOOGLE)
                )
            ).all()
        )


async def _google_connection(client) -> dict[str, str | None]:
    """The Google entry of the settings' connections"""
    settings = (await client.get(f"{PREFIX}/settings")).json()
    return next(c for c in settings["connections"] if c["id"] == "google")


async def test_connect_without_credentials_says_what_to_set(client, monkeypatch):
    monkeypatch.setenv("OPS_API_GOOGLE__CLIENT_ID", "")
    reload_settings()

    response = await client.get(CONNECT)

    assert response.status_code == 503
    assert "OPS_API_GOOGLE__CLIENT_ID" in response.json()["detail"]
    assert await _google_connection(client) == {
        "id": "google",
        "status": "not_configured",
        "account": None,
        "quota": None,
    }


async def test_connect_asks_google_offline_to_read_and_send_mail_and_add_events(client):
    response = await client.get(CONNECT)

    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    query = {key: values[0] for key, values in parse_qs(location.query).items()}
    assert location.netloc == "accounts.google.com"
    assert query["client_id"] == "client.test"
    assert query["redirect_uri"].endswith("/ops-api/v1/integrations/google/callback")
    assert query["scope"] == GOOGLE_SCOPES
    assert query["access_type"] == "offline"
    assert query["prompt"] == "consent"
    assert len(query["state"]) >= 32


async def test_callback_stores_the_refresh_token_encrypted(app, client):
    response = await connect_google(client, next_path="/inbox")

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:5174/inbox"
    [account] = await _accounts(app)
    assert account.account == "kelvin@gmail.com"
    assert b"refresh-1" not in account.secret
    assert Fernet(ENCRYPTION_KEY).decrypt(account.secret) == b"refresh-1"
    assert account.details == GoogleDetails(scopes=GOOGLE_SCOPES.split())
    assert await _google_connection(client) == {
        "id": "google",
        "status": "connected",
        "account": "kelvin@gmail.com",
        "quota": None,
    }


async def test_a_grant_from_before_send_and_events_needs_reconnecting(app, client):
    await connect_google(client)
    async with app.state.session_factory() as session, session.begin():
        await session.execute(
            update(Connection).values(
                details=GoogleDetails(
                    scopes=[
                        "https://www.googleapis.com/auth/gmail.readonly",
                        "https://www.googleapis.com/auth/calendar.readonly",
                    ]
                )
            )
        )

    before = await _google_connection(client)
    await connect_google(client)

    assert before == {
        "id": "google",
        "status": "needs_reconnect",
        "account": "kelvin@gmail.com",
        "quota": None,
    }
    assert (await _google_connection(client))["status"] == "connected"


async def test_connecting_again_replaces_the_token(app, client):
    await connect_google(client)
    async with app.state.session_factory() as session, session.begin():
        await session.execute(
            update(Connection).values(
                account="old@gmail.com",
                secret=Fernet(ENCRYPTION_KEY).encrypt(b"refresh-0"),
            )
        )

    await connect_google(client)

    [account] = await _accounts(app)
    assert account.account == "kelvin@gmail.com"
    assert Fernet(ENCRYPTION_KEY).decrypt(account.secret) == b"refresh-1"


async def test_callback_with_another_state_stores_nothing(app, client):
    await client.get(CONNECT)

    response = await client.get(CALLBACK, params={"code": "c", "state": "forged"})

    assert response.headers["location"].endswith("/settings?google_error=failed")
    assert await _accounts(app) == []


async def test_a_callback_finished_by_another_user_stores_nothing(app, client):
    start = await client.get(CONNECT)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    app.dependency_overrides[current_user] = lambda: User(
        id=uuid4(), email="other@example.com"
    )

    response = await client.get(CALLBACK, params={"code": "code-1", "state": state})

    app.dependency_overrides.clear()
    assert response.headers["location"].endswith("/settings?google_error=failed")
    assert await _accounts(app) == []


async def test_declining_on_google_goes_back_to_settings(app, client):
    await client.get(CONNECT)

    response = await client.get(CALLBACK, params={"error": "access_denied"})

    assert response.headers["location"].endswith("/settings?google_error=denied")
    assert await _accounts(app) == []


async def test_both_gmail_and_calendar_must_be_allowed(app, client, google):
    google.scope = "https://www.googleapis.com/auth/gmail.readonly"

    response = await connect_google(client)

    assert response.headers["location"].endswith("/settings?google_error=scopes")
    assert await _accounts(app) == []


async def test_disconnect_revokes_and_forgets_the_token(app, client, google):
    await connect_google(client)

    removed = await client.delete(f"{PREFIX}/integrations/google")
    again = await client.delete(f"{PREFIX}/integrations/google")

    assert removed.status_code == 204
    assert again.status_code == 204
    assert google.revoked_tokens == ["refresh-1"]
    assert await _accounts(app) == []
    assert (await _google_connection(client))["status"] == "not_connected"


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_the_granted_scopes_are_stored_in_the_details(postgres_app):
    async with _client(postgres_app) as client:
        await connect_google(client)

    async with postgres_app.state.session_factory() as session:
        stored = (
            await session.execute(
                text(
                    "SELECT pg_typeof(details)::text, details FROM connections "
                    "WHERE provider = 'google'"
                )
            )
        ).one()
    assert tuple(stored) == (
        "jsonb",
        {"provider": "google", "scopes": GOOGLE_SCOPES.split()},
    )
