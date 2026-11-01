import pytest
from pydantic import ValidationError

from src.core.config import BrowserSettings, ObservabilitySettings, Settings

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


def test_env_overrides_toml(monkeypatch):
    monkeypatch.setenv(
        "ARTIFACT_SERVICE_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318"
    )
    monkeypatch.setenv("ARTIFACT_SERVICE_OBSERVABILITY__TRACING_ENABLED", "true")
    monkeypatch.setenv(
        "ARTIFACT_SERVICE_OBSERVABILITY__METRICS_EXPORT_INTERVAL_MS", "5000"
    )
    monkeypatch.setenv("ARTIFACT_SERVICE_APP__ENV", "staging")

    settings = Settings(_env_file=None)

    assert str(settings.observability.otlp_endpoint) == "http://collector:4318/"
    assert settings.observability.metrics_export_interval_ms == 5000
    assert settings.observability.tracing_enabled is True
    assert settings.app.env == "staging"
    assert settings.app.name == "artifact-service"


def test_concurrent_renders_come_from_env(monkeypatch):
    monkeypatch.setenv("ARTIFACT_SERVICE_BROWSER__MAX_CONCURRENT_RENDERS", "2")

    assert Settings(_env_file=None).browser.max_concurrent_renders == 2


def test_concurrent_renders_must_be_positive():
    with pytest.raises(ValidationError):
        BrowserSettings(max_concurrent_renders=0)


def test_otlp_headers_are_secret(monkeypatch):
    monkeypatch.setenv(
        "ARTIFACT_SERVICE_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318"
    )
    monkeypatch.setenv(
        "ARTIFACT_SERVICE_OBSERVABILITY__OTLP_HEADERS", "Authorization=Basic abc"
    )

    settings = Settings(_env_file=None)

    assert "abc" not in repr(settings.observability)
    assert (
        settings.observability.otlp_headers.get_secret_value()
        == "Authorization=Basic abc"
    )
