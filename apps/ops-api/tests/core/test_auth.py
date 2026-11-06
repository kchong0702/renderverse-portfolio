from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from src.core.auth.models import AuthIdentity, AuthSession, SignInAttempts
from src.core.auth.repository import AuthRepository
from src.core.auth.service import AuthService
from src.core.config import get_settings, reload_settings
from src.core.db.base import utcnow
from tests.conftest import OWNER, PREFIX

PASSWORD = "correct horse battery"
WEB_URL = "http://localhost:5174"


async def _set_password(app, email: str = OWNER, password: str = PASSWORD) -> None:
    async with app.state.session_factory() as session:
        service = AuthService(AuthRepository(session), get_settings().auth)
        await service.set_password(email, password)
        await session.commit()


async def _sign_in(client, password: str = PASSWORD, email: str = OWNER):
    return await client.post(
        f"{PREFIX}/auth/password", json={"email": email, "password": password}
    )


async def _count(app, model) -> int:
    async with app.state.session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


# --- auth disabled ---


async def test_me_is_the_dev_email_while_auth_is_off(client):
    response = await client.get(f"{PREFIX}/me")

    assert response.status_code == 200
    assert response.json()["email"] == "owner@localhost"


# --- sessions ---


async def test_me_needs_a_session(auth_client):
    response = await auth_client.get(f"{PREFIX}/me")

    assert response.status_code == 401


async def test_expired_session_is_rejected(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    async with auth_app.state.session_factory() as session:
        await session.execute(
            update(AuthSession).values(expires_at=utcnow() - timedelta(minutes=1))
        )
        await session.commit()

    response = await auth_client.get(f"{PREFIX}/me")

    assert response.status_code == 401


async def test_session_ends_when_removed_from_the_allowlist(
    auth_app, auth_client, monkeypatch
):
    await _set_password(auth_app)
    await _sign_in(auth_client)

    monkeypatch.setenv("OPS_API_AUTH__ALLOWED_EMAILS", "someone-else@example.com")
    reload_settings()
    response = await auth_client.get(f"{PREFIX}/me")

    assert response.status_code == 401


async def test_sign_out_ends_the_session(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    token = auth_client.cookies["ops_session"]

    response = await auth_client.post(f"{PREFIX}/auth/sign-out")

    assert response.status_code == 204
    assert "ops_session" not in auth_client.cookies
    auth_client.cookies.set("ops_session", token, path="/ops-api")
    assert (await auth_client.get(f"{PREFIX}/me")).status_code == 401


# --- email and password ---


async def test_password_sign_in_sets_a_session_cookie(auth_app, auth_client):
    await _set_password(auth_app)

    response = await _sign_in(auth_client, email="  Owner@Example.com ")

    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("ops_session=")
    assert "HttpOnly" in cookie
    assert "Path=/ops-api" in cookie
    assert "SameSite=lax" in cookie
    me = await auth_client.get(f"{PREFIX}/me")
    assert me.status_code == 200
    assert me.json()["email"] == OWNER


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (OWNER, "wrong password here"),
        ("nobody@example.com", PASSWORD),
    ],
    ids=["wrong-password", "unknown-email"],
)
async def test_bad_credentials_get_the_same_answer(
    auth_app, auth_client, email, password
):
    await _set_password(auth_app)

    response = await _sign_in(auth_client, password=password, email=email)

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"
    assert "set-cookie" not in response.headers


async def test_user_without_a_password_cannot_use_one(auth_client):
    response = await _sign_in(auth_client)

    assert response.status_code == 401


async def test_repeated_failures_are_throttled(auth_app, auth_client):
    await _set_password(auth_app)
    for _ in range(5):
        assert (await _sign_in(auth_client, password="nope")).status_code == 401

    response = await _sign_in(auth_client)

    assert response.status_code == 429


async def test_unknown_emails_are_throttled_the_same(auth_client):
    for _ in range(5):
        assert (await _sign_in(auth_client, email="x@example.com")).status_code == 401

    response = await _sign_in(auth_client, email="x@example.com")

    assert response.status_code == 429


async def test_signing_in_clears_the_attempts(auth_app, auth_client):
    await _set_password(auth_app)
    for _ in range(4):
        await _sign_in(auth_client, password="nope")

    assert (await _sign_in(auth_client)).status_code == 204
    assert await _count(auth_app, SignInAttempts) == 0


async def test_attempts_start_again_after_the_window(
    auth_app, auth_client, monkeypatch
):
    await _set_password(auth_app)
    for _ in range(5):
        await _sign_in(auth_client, password="nope")

    later = utcnow() + timedelta(minutes=16)
    monkeypatch.setattr("src.core.auth.service.utcnow", lambda: later)

    assert (await _sign_in(auth_client)).status_code == 204


async def test_setting_a_password_lifts_the_lock(auth_app, auth_client):
    await _set_password(auth_app)
    for _ in range(6):
        await _sign_in(auth_client, password="nope")

    await _set_password(auth_app, password="a brand new password")

    response = await _sign_in(auth_client, password="a brand new password")
    assert response.status_code == 204


async def test_set_password_rules(auth_app):
    from src.core.exceptions import InvalidInput

    with pytest.raises(InvalidInput, match="not in auth.allowed_emails"):
        await _set_password(auth_app, email="nobody@example.com")
    with pytest.raises(InvalidInput, match="at least 12"):
        await _set_password(auth_app, password="short")


# --- Google and GitHub ---


async def test_sign_in_methods(auth_client):
    response = await auth_client.get(f"{PREFIX}/auth/methods")

    assert response.json() == {
        "required": True,
        "password": True,
        "google": True,
        "github": True,
    }


async def test_oauth_login_redirects_with_the_web_callback(
    auth_client, oauth_providers
):
    response = await auth_client.get(f"{PREFIX}/auth/google/login?next=/jobs")

    assert response.status_code == 307
    assert response.headers["location"] == "https://provider.test/authorize"
    assert (
        oauth_providers["google"].redirect_uri
        == f"{WEB_URL}/ops-api/v1/auth/google/callback"
    )


async def test_oauth_callback_signs_in_and_returns_to_next(auth_app, auth_client):
    await auth_client.get(f"{PREFIX}/auth/google/login?next=/jobs")

    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.status_code == 303
    assert response.headers["location"] == f"{WEB_URL}/jobs"
    assert (await auth_client.get(f"{PREFIX}/me")).json()["email"] == OWNER


async def test_next_cannot_leave_ops_web(auth_client):
    await auth_client.get(f"{PREFIX}/auth/google/login?next=//evil.test")

    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.headers["location"] == f"{WEB_URL}/"


async def test_google_and_github_with_one_email_are_one_user(auth_app, auth_client):
    await auth_client.get(f"{PREFIX}/auth/google/login")
    await auth_client.get(f"{PREFIX}/auth/google/callback")
    first = (await auth_client.get(f"{PREFIX}/me")).json()
    await auth_client.post(f"{PREFIX}/auth/sign-out")

    # GitHub's primary email is not allowlisted; its second verified one is
    await auth_client.get(f"{PREFIX}/auth/github/login")
    await auth_client.get(f"{PREFIX}/auth/github/callback")
    second = (await auth_client.get(f"{PREFIX}/me")).json()

    assert second == first
    assert await _count(auth_app, AuthIdentity) == 2


async def test_linked_account_keeps_working_after_its_email_changes(
    auth_client, oauth_providers
):
    await auth_client.get(f"{PREFIX}/auth/google/login")
    await auth_client.get(f"{PREFIX}/auth/google/callback")
    await auth_client.post(f"{PREFIX}/auth/sign-out")

    oauth_providers["google"].identity.emails[:] = ["renamed@example.com"]
    await auth_client.get(f"{PREFIX}/auth/google/login")
    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.headers["location"] == f"{WEB_URL}/"
    assert (await auth_client.get(f"{PREFIX}/me")).json()["email"] == OWNER


async def test_oauth_account_not_allowlisted_is_sent_back(
    auth_app, auth_client, oauth_providers
):
    oauth_providers["google"].identity.emails[:] = ["stranger@example.com"]
    await auth_client.get(f"{PREFIX}/auth/google/login")

    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert "ops_session" not in auth_client.cookies
    assert await _count(auth_app, AuthIdentity) == 0


async def test_cancelled_oauth_is_sent_back(auth_client, oauth_providers):
    oauth_providers["github"].fails = True
    await auth_client.get(f"{PREFIX}/auth/github/login")

    response = await auth_client.get(f"{PREFIX}/auth/github/callback")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=failed"


async def test_unconfigured_provider_is_not_found(auth_client, oauth_providers):
    del oauth_providers["github"]

    response = await auth_client.get(f"{PREFIX}/auth/github/login")

    assert response.status_code == 404


# --- cross-site requests ---


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        # Sec-Fetch-Site decides when the browser sends it
        ({"Sec-Fetch-Site": "same-origin"}, 204),
        ({"Sec-Fetch-Site": "none"}, 204),
        ({"Sec-Fetch-Site": "same-site", "Origin": "https://other.localhost"}, 403),
        ({"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.test"}, 403),
        # ops-web's own origin is trusted whatever Sec-Fetch-Site says
        ({"Sec-Fetch-Site": "cross-site", "Origin": WEB_URL}, 204),
        # Browsers without Sec-Fetch-Site: Origin decides
        ({"Origin": WEB_URL}, 204),
        ({"Origin": "https://evil.test"}, 403),
        # Neither header: not a browser, so no ambient cookie to abuse
        ({}, 204),
    ],
)
async def test_cross_site_writes_are_blocked(auth_app, auth_client, headers, status):
    await _set_password(auth_app)

    response = await auth_client.post(
        f"{PREFIX}/auth/password",
        json={"email": OWNER, "password": PASSWORD},
        headers=headers,
    )

    assert response.status_code == status
