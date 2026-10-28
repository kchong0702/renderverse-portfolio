import pytest
from pydantic import ValidationError

from src.core.config import ObservabilitySettings, Settings

pytestmark = pytest.mark.usefixtures("isolate_env")


def test_exporters_disabled_by_default():
    obs = ObservabilitySettings()

    assert obs.tracing_enabled is False
    assert obs.metrics_enabled is False
    assert obs.otlp_endpoint is None


@pytest.mark.parametrize("signal", ["tracing", "metrics"])
def test_enabled_signal_requires_endpoint(signal):
    with pytest.raises(ValidationError, match=f"{signal}_enabled is True"):
        ObservabilitySettings(**{f"{signal}_enabled": True})


def test_toml_requires_endpoint_from_env():
    # config.toml enables tracing and metrics, the endpoint is expected from .env
    with pytest.raises(ValidationError, match="otlp_endpoint is not set"):
        Settings(_env_file=None)


def test_env_overrides_toml(monkeypatch):
    monkeypatch.setenv("EZBOT_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("EZBOT_OBSERVABILITY__METRICS_EXPORT_INTERVAL_MS", "5000")
    monkeypatch.setenv("EZBOT_APP__ENV", "staging")

    settings = Settings(_env_file=None)

    assert str(settings.observability.otlp_endpoint) == "http://collector:4318/"
    assert settings.observability.metrics_export_interval_ms == 5000
    assert settings.observability.tracing_enabled is True
    assert settings.observability.instrumentations == ("langchain",)
    assert settings.app.env == "staging"
    assert settings.app.name == "ezbot"


def test_otlp_headers_are_secret(monkeypatch):
    monkeypatch.setenv("EZBOT_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("EZBOT_OBSERVABILITY__OTLP_HEADERS", "Authorization=Basic abc")

    settings = Settings(_env_file=None)

    assert "abc" not in repr(settings.observability)
    assert (
        settings.observability.otlp_headers.get_secret_value()
        == "Authorization=Basic abc"
    )
