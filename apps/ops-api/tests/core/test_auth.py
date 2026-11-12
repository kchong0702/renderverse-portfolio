from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Engine, create_engine, func, select, update
from sqlalchemy.orm import Session

from src.core.auth.cli import main
from src.core.auth.enums import Role
from src.core.auth.models import AuthIdentity, AuthSession, User
from src.core.auth.oauth_providers import OAuthIdentity
from src.core.auth.passwords import verify_password
from src.core.auth.service import AuthService
from src.core.config import get_settings, reload_settings
from src.db.base import Base, utcnow
from tests.conftest import OWNER, PREFIX

PASSWORD = "correct horse battery"
WEB_URL = "http://localhost:5174"
OTHER = "other@example.com"


async def _set_password(app, email: str = OWNER, password: str = PASSWORD) -> None:
    async with app.state.session_factory() as session:
        service = AuthService(session, get_settings().auth)
        await service.set_password(email, password)
        await session.commit()


async def _sign_in(client, password: str = PASSWORD, email: str = OWNER):
    return await client.post(
        f"{PREFIX}/auth/password", json={"email": email, "password": password}
    )


async def _sign_in_with(client, provider: str):
    """Sign in through the provider's login and callback; returns the callback"""
    await client.get(f"{PREFIX}/auth/{provider}/login")
    return await client.get(f"{PREFIX}/auth/{provider}/callback")


async def _link(client, provider: str):
    """Link the provider's account from Settings; returns the callback"""
    await client.get(f"{PREFIX}/auth/{provider}/link?next=/settings")
    return await client.get(f"{PREFIX}/auth/{provider}/callback")


async def _seed(app, email: str) -> None:
    """Add a user with no sign-in method yet"""
    async with app.state.session_factory() as session, session.begin():
        session.add(User(email=email))


async def _disable(app, email: str = OWNER) -> None:
    """Revoke the user's access"""
    async with app.state.session_factory() as session, session.begin():
        await session.execute(
            update(User).where(User.email == email).values(disabled_at=utcnow())
        )


async def _linked(client) -> dict[str, str | None]:
    """The signed-in user's linked email per sign-in method"""
    response = await client.get(f"{PREFIX}/auth/identities")
    return {method["provider"]: method["email"] for method in response.json()}


async def _count(app, model) -> int:
    async with app.state.session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_me_is_the_dev_email_while_auth_is_off(client):
    response = await client.get(f"{PREFIX}/me")

    assert response.status_code == 200
    assert response.json()["email"] == "owner@localhost"
    assert response.json()["role"] == "admin"


async def test_a_new_password_user_is_a_user(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)

    response = await auth_client.get(f"{PREFIX}/me")

    assert response.json()["role"] == "user"


async def test_a_new_sso_user_is_a_user(auth_client):
    await _sign_in_with(auth_client, "google")

    me = (await auth_client.get(f"{PREFIX}/me")).json()

    assert (me["email"], me["role"]) == (OWNER, "user")


async def test_me_shows_the_role_set_in_the_database(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    async with auth_app.state.session_factory() as session:
        await session.execute(update(User).values(role=Role.ADMIN))
        await session.commit()

    response = await auth_client.get(f"{PREFIX}/me")

    assert response.json()["role"] == "admin"


async def test_me_needs_a_session(auth_client):
    response = await auth_client.get(f"{PREFIX}/me")

    assert response.status_code == 401


async def test_settings_need_a_session(auth_client):
    response = await auth_client.get(f"{PREFIX}/settings")

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


async def test_session_ends_when_the_user_is_disabled(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)

    await _disable(auth_app)
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


async def test_disabled_user_cannot_sign_in_with_a_password(auth_app, auth_client):
    await _set_password(auth_app)
    await _disable(auth_app)

    response = await _sign_in(auth_client)

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


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


async def test_signing_in_clears_the_emails_attempts(auth_app, auth_client):
    await _set_password(auth_app)
    for _ in range(4):
        await _sign_in(auth_client, password="nope")

    assert (await _sign_in(auth_client)).status_code == 204
    for _ in range(5):
        assert (await _sign_in(auth_client, password="nope")).status_code == 401
    assert (await _sign_in(auth_client)).status_code == 429


async def test_one_client_is_throttled_across_emails(auth_client):
    for i in range(20):
        response = await _sign_in(auth_client, email=f"x{i}@example.com")
        assert response.status_code == 401

    response = await _sign_in(auth_client, email="y@example.com")

    assert response.status_code == 429


async def test_signing_in_keeps_the_clients_attempts(auth_app, auth_client):
    await _set_password(auth_app)
    for i in range(19):
        await _sign_in(auth_client, email=f"x{i}@example.com")
    assert (await _sign_in(auth_client)).status_code == 204

    response = await _sign_in(auth_client, email="y@example.com")

    assert response.status_code == 429


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


async def test_setting_a_password_replaces_the_old_one(auth_app, auth_client):
    await _set_password(auth_app)

    await _set_password(auth_app, password="a brand new password")

    assert (await _sign_in(auth_client)).status_code == 401
    assert (
        await _sign_in(auth_client, password="a brand new password")
    ).status_code == 204
    assert await _count(auth_app, AuthIdentity) == 1


async def test_set_password_rules(auth_app):
    from src.core.exceptions import InvalidInput

    await _seed(auth_app, OTHER)
    await _disable(auth_app, OTHER)

    with pytest.raises(InvalidInput, match="not a user"):
        await _set_password(auth_app, email="nobody@example.com")
    with pytest.raises(InvalidInput, match="disabled"):
        await _set_password(auth_app, email=OTHER)
    with pytest.raises(InvalidInput, match="at least 12"):
        await _set_password(auth_app, password="short")
    assert await _count(auth_app, User) == 2


@pytest.fixture
def cli_database(monkeypatch, tmp_path) -> Iterator[Engine]:
    """A SQLite database with OWNER seeded, for the command line to run against"""
    engine = create_engine(f"sqlite:///{tmp_path}/ops.db")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add(User(email=OWNER))
    monkeypatch.setenv(
        "OPS_API_DATABASE__URL", f"sqlite+aiosqlite:///{tmp_path}/ops.db"
    )
    monkeypatch.setattr("src.core.auth.cli.getpass", lambda prompt: PASSWORD)
    reload_settings()
    yield engine
    engine.dispose()
    get_settings.cache_clear()


def test_set_password_command_sets_a_users_password(cli_database, capsys):
    main(["set-password", OWNER])

    with Session(cli_database) as session:
        identity = session.scalar(select(AuthIdentity))
    assert identity is not None
    assert (identity.provider, identity.email) == ("password", OWNER)
    assert verify_password(PASSWORD, identity.secret_hash)[0]
    assert capsys.readouterr().out == f"Password set for {OWNER}\n"


def test_set_password_command_refuses_an_unknown_email(cli_database, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["set-password", "nobody@example.com"])

    assert exit_info.value.code == 1
    assert "not a user" in capsys.readouterr().err


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


async def test_another_account_with_a_claimed_email_is_refused(auth_app, auth_client):
    await _sign_in_with(auth_client, "google")
    await auth_client.post(f"{PREFIX}/auth/sign-out")

    response = await _sign_in_with(auth_client, "github")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert await _count(auth_app, AuthIdentity) == 1


async def test_sso_cannot_claim_a_user_with_a_password(auth_app, auth_client):
    await _set_password(auth_app)

    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"


async def test_linked_account_keeps_working_after_its_email_changes(
    auth_client, oauth_providers
):
    await _sign_in_with(auth_client, "google")
    await auth_client.post(f"{PREFIX}/auth/sign-out")

    oauth_providers["google"].identity.emails[:] = ["renamed@example.com"]
    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/"
    assert (await auth_client.get(f"{PREFIX}/me")).json()["email"] == OWNER


async def test_oauth_account_of_no_user_is_sent_back(
    auth_app, auth_client, oauth_providers
):
    oauth_providers["google"].identity.emails[:] = ["stranger@example.com"]

    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert "ops_session" not in auth_client.cookies
    assert await _count(auth_app, AuthIdentity) == 0


async def test_disabled_user_cannot_claim_an_account(auth_app, auth_client):
    await _disable(auth_app)

    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert await _count(auth_app, AuthIdentity) == 0


async def test_disabled_user_cannot_sign_in_with_a_linked_account(
    auth_app, auth_client
):
    await _sign_in_with(auth_client, "google")
    await auth_client.post(f"{PREFIX}/auth/sign-out")
    await _disable(auth_app)

    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert "ops_session" not in auth_client.cookies


async def test_cancelled_oauth_is_sent_back(auth_client, oauth_providers):
    oauth_providers["github"].fails = True

    response = await _sign_in_with(auth_client, "github")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=failed"


async def test_unconfigured_provider_is_not_found(auth_client, oauth_providers):
    del oauth_providers["github"]

    response = await auth_client.get(f"{PREFIX}/auth/github/login")

    assert response.status_code == 404


async def test_identities_list_every_method(auth_app, auth_client, oauth_providers):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    await _link(auth_client, "google")
    del oauth_providers["github"]

    response = await auth_client.get(f"{PREFIX}/auth/identities")

    assert response.json() == [
        {"provider": "password", "email": OWNER, "configured": True},
        {"provider": "google", "email": OWNER, "configured": True},
        {"provider": "github", "email": None, "configured": False},
    ]


async def test_identities_need_a_session(auth_client):
    response = await auth_client.get(f"{PREFIX}/auth/identities")

    assert response.status_code == 401


async def test_linking_attaches_the_account_to_the_signed_in_user(
    auth_app, auth_client, oauth_providers
):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    oauth_providers["github"].identity = OAuthIdentity("github-1", [OTHER])

    response = await _link(auth_client, "github")

    assert response.status_code == 303
    assert response.headers["location"] == f"{WEB_URL}/settings"
    assert (await _linked(auth_client))["github"] == OTHER
    await auth_client.post(f"{PREFIX}/auth/sign-out")
    await _sign_in_with(auth_client, "github")
    assert (await auth_client.get(f"{PREFIX}/me")).json()["email"] == OWNER


async def test_linking_needs_a_session(auth_client):
    response = await auth_client.get(f"{PREFIX}/auth/google/link")

    assert response.status_code == 401


async def test_linking_refuses_an_account_linked_to_someone_else(
    auth_app, auth_client, oauth_providers
):
    await _seed(auth_app, OTHER)
    oauth_providers["google"].identity = OAuthIdentity("google-1", [OTHER])
    await _sign_in_with(auth_client, "google")
    await auth_client.post(f"{PREFIX}/auth/sign-out")
    await _set_password(auth_app)
    await _sign_in(auth_client)

    response = await _link(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=taken"
    assert (await _linked(auth_client))["google"] is None


async def test_linking_refuses_a_second_account_of_one_provider(
    auth_app, auth_client, oauth_providers
):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    await _link(auth_client, "google")
    oauth_providers["google"].identity = OAuthIdentity("google-2", [OTHER])

    response = await _link(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=taken"
    assert (await _linked(auth_client))["google"] == OWNER


async def test_linking_refuses_an_account_without_a_verified_email(
    auth_app, auth_client, oauth_providers
):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    oauth_providers["github"].identity = OAuthIdentity("github-1", [])

    response = await _link(auth_client, "github")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=unverified"
    assert (await _linked(auth_client))["github"] is None


async def test_linking_fails_when_the_user_signed_out_meanwhile(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    await auth_client.get(f"{PREFIX}/auth/google/link")
    await auth_client.post(f"{PREFIX}/auth/sign-out")

    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=failed"
    assert await _count(auth_app, AuthIdentity) == 1


async def test_linking_fails_for_another_signed_in_user(auth_app, auth_client):
    await _seed(auth_app, OTHER)
    await _set_password(auth_app)
    await _set_password(auth_app, email=OTHER)
    await _sign_in(auth_client)
    await auth_client.get(f"{PREFIX}/auth/google/link")
    await auth_client.post(f"{PREFIX}/auth/sign-out")
    await _sign_in(auth_client, email=OTHER)

    response = await auth_client.get(f"{PREFIX}/auth/google/callback")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=failed"
    assert (await _linked(auth_client))["google"] is None


async def test_cancelled_linking_is_sent_back_to_settings(
    auth_app, auth_client, oauth_providers
):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    oauth_providers["google"].fails = True

    response = await _link(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/settings?link_error=failed"


async def test_signing_in_drops_a_stale_link(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    await auth_client.get(f"{PREFIX}/auth/google/link")

    response = await _sign_in_with(auth_client, "google")

    assert response.headers["location"] == f"{WEB_URL}/sign-in?error=not_allowed"
    assert (await _linked(auth_client))["google"] is None


@pytest.mark.parametrize("provider", ["password", "google"])
async def test_unlinking_removes_a_sign_in_method(auth_app, auth_client, provider):
    await _set_password(auth_app)
    await _sign_in(auth_client)
    await _link(auth_client, "google")

    response = await auth_client.delete(f"{PREFIX}/auth/identities/{provider}")

    assert response.status_code == 204
    assert (await _linked(auth_client))[provider] is None


async def test_the_last_sign_in_method_cannot_be_removed(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)

    response = await auth_client.delete(f"{PREFIX}/auth/identities/password")

    assert response.status_code == 409
    assert response.json()["detail"] == "You can't remove your last sign-in method"
    assert (await _linked(auth_client))["password"] == OWNER


async def test_unlinking_a_method_not_linked_is_not_found(auth_app, auth_client):
    await _set_password(auth_app)
    await _sign_in(auth_client)

    response = await auth_client.delete(f"{PREFIX}/auth/identities/github")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"Sec-Fetch-Site": "same-origin"}, 204),
        ({"Sec-Fetch-Site": "none"}, 204),
        ({"Sec-Fetch-Site": "same-site", "Origin": "https://other.localhost"}, 403),
        ({"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.test"}, 403),
        ({"Sec-Fetch-Site": "cross-site", "Origin": WEB_URL}, 204),
        ({"Origin": WEB_URL}, 204),
        ({"Origin": "https://evil.test"}, 403),
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
