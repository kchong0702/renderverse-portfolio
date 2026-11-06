import pytest
from pydantic import ValidationError

from src.core.config import AuthSettings, Settings


def test_list_settings_take_comma_separated_env_vars(monkeypatch):
    monkeypatch.setenv("OPS_API_AUTH__ALLOWED_EMAILS", "A@x.com, b@x.com")
    monkeypatch.setenv("OPS_API_APP__CORS_ORIGIN", "http://a,http://b")

    settings = Settings()

    assert settings.auth.allowed_emails == ["a@x.com", "b@x.com"]
    assert settings.app.cors_origin == ["http://a", "http://b"]


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"secret_key": "k" * 32}, "allowed_emails is empty"),
        ({"allowed_emails": ["a@x.com"]}, "secret_key of 32"),
        ({"allowed_emails": ["a@x.com"], "secret_key": "short"}, "secret_key of 32"),
    ],
    ids=["no-allowlist", "no-key", "short-key"],
)
def test_enabled_auth_needs_an_allowlist_and_a_key(values, message):
    with pytest.raises(ValidationError, match=message):
        AuthSettings(enabled=True, **values)


def test_cookies_are_secure_on_https():
    assert AuthSettings(web_url="https://ops.example.ts.net/").secure_cookies
    assert not AuthSettings(web_url="http://localhost:5174").secure_cookies
