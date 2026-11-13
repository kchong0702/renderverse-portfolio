import pytest
from pydantic import ValidationError

from src.core.config import AuthSettings, JSearchSettings, Settings


def test_list_settings_take_comma_separated_env_vars(monkeypatch):
    monkeypatch.setenv("OPS_API_APP__CORS_ORIGIN", "http://a,http://b")

    settings = Settings()

    assert settings.app.cors_origin == ["http://a", "http://b"]


@pytest.mark.parametrize(
    "values", [{}, {"secret_key": "short"}], ids=["no-key", "short-key"]
)
def test_enabled_auth_needs_a_key(values):
    with pytest.raises(ValidationError, match="secret_key of 32"):
        AuthSettings(enabled=True, **values)


@pytest.mark.parametrize(
    ("env", "web_url"),
    [("prod", "http://localhost:5174"), ("dev", "https://ops.example.ts.net")],
    ids=["prod", "remote-web-url"],
)
def test_disabled_auth_refuses_to_start_outside_local_dev(env, web_url):
    with pytest.raises(ValidationError, match="app.env dev and a localhost"):
        Settings(app={"env": env}, auth={"enabled": False, "web_url": web_url})


@pytest.mark.parametrize(
    "web_url", ["http://localhost:5174", "http://127.0.0.1:5174", "http://[::1]:5174"]
)
def test_disabled_auth_starts_in_local_dev(web_url):
    settings = Settings(app={"env": "dev"}, auth={"enabled": False, "web_url": web_url})

    assert not settings.auth.enabled


def test_enabled_auth_starts_anywhere():
    settings = Settings(
        app={"env": "prod"},
        auth={
            "enabled": True,
            "secret_key": "k" * 32,
            "web_url": "https://ops.example.ts.net",
        },
    )

    assert settings.auth.enabled


def test_cookies_are_secure_on_https():
    assert AuthSettings(web_url="https://ops.example.ts.net/").secure_cookies
    assert not AuthSettings(web_url="http://localhost:5174").secure_cookies


def test_a_jsearch_encryption_key_fernet_cannot_use_fails_at_startup():
    with pytest.raises(ValidationError, match="Fernet key"):
        JSearchSettings(encryption_key="not-a-fernet-key")
