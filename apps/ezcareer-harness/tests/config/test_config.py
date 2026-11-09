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


def test_env_overrides_toml(monkeypatch):
    monkeypatch.setenv(
        "EZCAREER_HARNESS_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318"
    )
    monkeypatch.setenv("EZCAREER_HARNESS_OBSERVABILITY__TRACING_ENABLED", "true")
    monkeypatch.setenv(
        "EZCAREER_HARNESS_OBSERVABILITY__METRICS_EXPORT_INTERVAL_MS", "5000"
    )
    monkeypatch.setenv("EZCAREER_HARNESS_APP__ENV", "staging")

    settings = Settings(_env_file=None)

    assert str(settings.observability.otlp_endpoint) == "http://collector:4318/"
    assert settings.observability.metrics_export_interval_ms == 5000
    assert settings.observability.tracing_enabled is True
    assert settings.observability.instrumentations == ("langchain",)
    assert settings.app.env == "staging"
    assert settings.app.name == "ezcareer-harness"


def test_otlp_headers_are_secret(monkeypatch):
    monkeypatch.setenv(
        "EZCAREER_HARNESS_OBSERVABILITY__OTLP_ENDPOINT", "http://collector:4318"
    )
    monkeypatch.setenv(
        "EZCAREER_HARNESS_OBSERVABILITY__OTLP_HEADERS", "Authorization=Basic abc"
    )

    settings = Settings(_env_file=None)

    assert "abc" not in repr(settings.observability)
    assert (
        settings.observability.otlp_headers.get_secret_value()
        == "Authorization=Basic abc"
    )


def test_an_agent_on_a_model_the_catalog_does_not_offer_is_refused():
    with pytest.raises(ValidationError, match="glm-9, which \\[models\\] does not"):
        Settings(
            _env_file=None,
            models={"glm": ["glm-5.3"]},
            agents=[
                {
                    "name": "job-finder",
                    "path": "src/agents/job_finder/profile.yaml",
                    "family": "glm",
                    "model": "glm-9",
                }
            ],
        )
