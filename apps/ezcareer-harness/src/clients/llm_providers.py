from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.core.config import get_settings

PROVIDERS = {"claude": "anthropic", "glm": "openai", "openai": "openai"}
"""The LangChain provider each model family runs on"""


def llm_provider(family: str, name: str) -> BaseChatModel:
    """The chat model for an exact model name of a family; claude and openai models
    reason at the configured effort and summarise it, glm goes through the gateway"""
    settings = get_settings()
    if PROVIDERS[family] == "anthropic":
        return ChatAnthropic(
            model_name=name,
            thinking={"type": "adaptive", "display": "summarized"},
            reasoning_effort=settings.reasoning_effort,
        )
    if family == "openai":
        return ChatOpenAI(
            model=name,
            use_responses_api=True,
            reasoning={"effort": settings.reasoning_effort, "summary": "auto"},
        )
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
