import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from src.clients import llm_providers
from src.core.config import Settings


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("AIGW_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("AIGW_API_KEY", "sk-test")
    settings = Settings(_env_file=None)
    monkeypatch.setattr(llm_providers, "get_settings", lambda: settings)
    return settings


def test_glm_models_go_through_the_gateway(gateway: Settings):
    model = llm_providers.llm_provider("glm", "glm-5.3")

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-5.3"
    assert model.openai_api_base == "https://gateway.example/v1"
    assert model.openai_api_key.get_secret_value() == "sk-test"
    assert not model.use_responses_api
    assert model.stream_usage


def test_openai_models_go_to_openai_with_its_own_key(
    gateway: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    model = llm_providers.llm_provider("openai", "gpt-6-luna")

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-6-luna"
    assert model.openai_api_base is None
    assert model.openai_api_key.get_secret_value() == "sk-openai"
    assert model.use_responses_api
    assert model.reasoning == {"effort": "low", "summary": "auto"}


def test_claude_models_go_to_anthropic(gateway: Settings):
    model = llm_providers.llm_provider("claude", "claude-opus-5-5")

    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-opus-5-5"


def test_the_gateway_key_stays_secret(gateway: Settings):
    assert "sk-test" not in repr(gateway)


def test_gateway_models_need_the_gateway_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AIGW_BASE_URL", raising=False)
    monkeypatch.delenv("AIGW_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    monkeypatch.setattr(llm_providers, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="AIGW_BASE_URL"):
        llm_providers.llm_provider("glm", "glm-5.3")
