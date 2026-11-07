from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.core.config import get_settings

PROVIDERS = {"claude": "anthropic", "glm": "openai", "openai": "openai"}
"""The LangChain provider each model family runs on"""


def chat_model(family: str, name: str) -> BaseChatModel:
    """The chat model for an exact model name of a family; glm and openai
    models go through the model gateway"""
    if PROVIDERS[family] == "anthropic":
        return ChatAnthropic(model_name=name)
    settings = get_settings()
    if settings.gateway_url is None or settings.gateway_key is None:
        raise ValueError(
            f"{family} models need the gateway: set AIGW_UPSTREAM_URL and AIGW_PASSTHROUGH_KEY"
        )
    return ChatOpenAI(
        model=name,
        base_url=str(settings.gateway_url),
        api_key=settings.gateway_key,
        use_responses_api=False,
    )
