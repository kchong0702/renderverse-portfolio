from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Literal, Protocol

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict

from src.core.config import LLMSettings, ModelSettings, Provider
from src.features.llm.exceptions import (
    MissingCredentialsError,
    ModelConfigError,
    NoModelConfiguredError,
)
from src.infrastructure.observability.logging import get_logger


class ModelAdapter(Protocol):
    """Builds chat models for one provider"""

    def create(self, spec: ModelSettings) -> BaseChatModel:
        """Build the chat model described by `spec`"""
        ...


_logger = get_logger(__name__)

LangChainProvider = Literal["google_genai", "groq", "mistralai", "openai", "openrouter"]


def _common_kwargs(spec: ModelSettings) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "timeout": spec.timeout_s,
        "max_retries": spec.max_retries,
    }
    if spec.temperature is not None:
        kwargs["temperature"] = spec.temperature
    if spec.max_tokens is not None:
        kwargs["max_tokens"] = spec.max_tokens
    return kwargs


def _require_api_key(env_var: str) -> str:
    value = os.environ.get(env_var, "").strip()
    if not value:
        raise MissingCredentialsError(f"environment variable {env_var} is not set")
    return value


class LangChainAdapter(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_provider: LangChainProvider
    """`init_chat_model` provider key"""

    api_key_env: str
    """Environment variable the LangChain integration reads its key from"""

    def create(self, spec: ModelSettings) -> BaseChatModel:
        env_var = spec.api_key_env or self.api_key_env
        api_key = _require_api_key(env_var)
        if env_var != self.api_key_env:
            os.environ[self.api_key_env] = api_key
        if spec.base_url is not None:
            raise ModelConfigError(
                f"{spec.provider} does not take base_url; use openai_compatible"
            )
        return init_chat_model(
            spec.model, model_provider=self.model_provider, **_common_kwargs(spec)
        )


class OpenAICompatibleAdapter(BaseModel):
    model_config = ConfigDict(frozen=True)

    def create(self, spec: ModelSettings) -> BaseChatModel:
        if spec.base_url is None or spec.api_key_env is None:
            raise ModelConfigError("openai_compatible needs base_url and api_key_env")
        return ChatOpenAI(
            model=spec.model,
            base_url=str(spec.base_url),
            api_key=_require_api_key(spec.api_key_env),
            **_common_kwargs(spec),
        )


ADAPTERS: Mapping[Provider, ModelAdapter] = {
    "groq": LangChainAdapter(model_provider="groq", api_key_env="GROQ_API_KEY"),
    "mistralai": LangChainAdapter(
        model_provider="mistralai", api_key_env="MISTRAL_API_KEY"
    ),
    "google_genai": LangChainAdapter(
        model_provider="google_genai", api_key_env="GOOGLE_API_KEY"
    ),
    "openrouter": LangChainAdapter(
        model_provider="openrouter", api_key_env="OPENROUTER_API_KEY"
    ),
    "openai_compatible": OpenAICompatibleAdapter(),
}


def create_model(
    spec: ModelSettings, adapters: Mapping[Provider, ModelAdapter] = ADAPTERS
) -> BaseChatModel:
    """Build one chat model through its provider's adapter"""
    adapter = adapters.get(spec.provider)
    if adapter is None:
        raise ModelConfigError(
            f"unknown provider {spec.provider!r}, expected one of {sorted(adapters)}"
        )
    return adapter.create(spec)


def create_models(
    settings: LLMSettings, adapters: Mapping[Provider, ModelAdapter] = ADAPTERS
) -> list[BaseChatModel]:
    """Build the configured chat models in fallback order.

    Models whose API key is missing are skipped so a partial set of keys still
    starts; any other misconfiguration fails fast.
    """
    models: list[BaseChatModel] = []
    built: list[str] = []
    for spec in settings.models:
        try:
            models.append(create_model(spec, adapters))
        except MissingCredentialsError as exc:
            _logger.warning("Skipping model %s:%s, %s", spec.provider, spec.model, exc)
            continue
        built.append(f"{spec.provider}:{spec.model}")
    if not models:
        raise NoModelConfiguredError(
            "no chat model is configured: set an API key for at least one of "
            "llm.models (e.g. GROQ_API_KEY in apps/ezbot/.env)"
        )
    _logger.info("Chat models in fallback order: %s", ", ".join(built))
    return models


__all__ = [
    "ADAPTERS",
    "LangChainAdapter",
    "LangChainProvider",
    "ModelAdapter",
    "OpenAICompatibleAdapter",
    "create_model",
    "create_models",
]
