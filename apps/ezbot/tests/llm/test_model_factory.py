import os
from typing import get_args

import pytest
from langchain.chat_models.base import _BUILTIN_PROVIDERS
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.core.config import LLMSettings, ModelSettings, Provider
from src.features.llm.factory import (
    ADAPTERS,
    LangChainProvider,
    create_model,
    create_models,
)
from src.shared.exceptions import ModelConfigError, NoModelConfiguredError

PROVIDER_KEYS = [
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "ZAI_API_KEY",
]


@pytest.fixture(autouse=True)
def no_provider_keys(monkeypatch):
    for key in PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)


def spec(**kwargs) -> ModelSettings:
    return ModelSettings(**kwargs)


def test_preset_provider_builds_its_langchain_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "key")

    model = create_model(
        spec(provider="groq", model="openai/gpt-oss-120b", temperature=0.2)
    )

    assert isinstance(model, ChatGroq)
    assert model.temperature == 0.2


def test_openai_compatible_reaches_any_provider(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "key")

    model = create_model(
        spec(
            provider="openai_compatible",
            model="glm-4.7-flash",
            base_url="https://api.z.ai/api/paas/v4",
            api_key_env="ZAI_API_KEY",
        )
    )

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "https://api.z.ai/api/paas/v4"


def test_openai_compatible_needs_base_url_and_key_env():
    with pytest.raises(ModelConfigError):
        create_model(spec(provider="openai_compatible", model="m"))


def test_unknown_provider_is_rejected_by_settings():
    with pytest.raises(ValidationError, match="provider"):
        spec(provider="nope", model="m")


def test_every_provider_has_an_adapter():
    assert set(get_args(Provider)) == set(ADAPTERS)


def test_langchain_providers_are_known_to_init_chat_model():
    assert set(get_args(LangChainProvider)) <= set(_BUILTIN_PROVIDERS)


def test_provider_missing_from_adapters_is_rejected():
    with pytest.raises(ModelConfigError, match="unknown provider"):
        create_model(spec(provider="groq", model="m"), adapters={})


def test_custom_key_env_is_handed_to_the_integration(monkeypatch):
    monkeypatch.setenv("MY_MISTRAL", "key")

    model = create_model(
        spec(
            provider="mistralai", model="mistral-small-latest", api_key_env="MY_MISTRAL"
        )
    )

    assert isinstance(model, ChatMistralAI)
    assert os.environ["MISTRAL_API_KEY"] == "key"


def test_models_without_keys_are_skipped_in_fallback_order(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "key")
    settings = LLMSettings(
        models=[
            spec(provider="groq", model="openai/gpt-oss-120b"),
            spec(provider="mistralai", model="mistral-small-latest"),
        ]
    )

    models = create_models(settings)

    assert [type(m) for m in models] == [ChatMistralAI]


def test_no_usable_model_fails_at_startup():
    settings = LLMSettings(models=[spec(provider="groq", model="openai/gpt-oss-120b")])

    with pytest.raises(NoModelConfiguredError):
        create_models(settings)
