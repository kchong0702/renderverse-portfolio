from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ConfigDict, SecretStr


class RunContext(BaseModel):
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    model: BaseChatModel | None = None
    """The chat model every LLM call of the run uses instead of its configured one"""

    jsearch_api_key: SecretStr | None = None
    """The user's own RapidAPI key, which search_jobs uses instead of the server's"""
