import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from src.core.config import Settings
from src.shared.clients import chat_models


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("AIGW_UPSTREAM_URL", "https://gateway.example/v1")
    monkeypatch.setenv("AIGW_PASSTHROUGH_KEY", "sk-test")
    settings = Settings(_env_file=None)
    monkeypatch.setattr(chat_models, "get_settings", lambda: settings)
    return settings


def test_glm_models_go_through_the_gateway(gateway: Settings):
    model = chat_models.chat_model("glm", "glm-5.3")

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-5.3"
    assert model.openai_api_base == "https://gateway.example/v1"
    assert model.openai_api_key.get_secret_value() == "sk-test"
    assert not model.use_responses_api


def test_openai_models_go_to_openai_with_its_own_key(
    gateway: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    model = chat_models.chat_model("openai", "gpt-6-luna")

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-6-luna"
    assert model.openai_api_base is None
    assert model.openai_api_key.get_secret_value() == "sk-openai"
    assert model.use_responses_api


def test_claude_models_go_to_anthropic(gateway: Settings):
    model = chat_models.chat_model("claude", "claude-opus-5-5")

    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-opus-5-5"


def test_the_gateway_key_stays_secret(gateway: Settings):
    assert "sk-test" not in repr(gateway)


def test_gateway_models_need_the_gateway_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AIGW_UPSTREAM_URL", raising=False)
    monkeypatch.delenv("AIGW_PASSTHROUGH_KEY", raising=False)
    settings = Settings(_env_file=None)
    monkeypatch.setattr(chat_models, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="AIGW_UPSTREAM_URL"):
        chat_models.chat_model("glm", "glm-5.3")
