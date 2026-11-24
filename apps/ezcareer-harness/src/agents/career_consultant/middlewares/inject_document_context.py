from collections.abc import Awaitable, Callable
from functools import cache
from pathlib import Path
from string import Template

from langchain.agents.middleware import (
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    wrap_model_call,
)
from langchain_core.messages import HumanMessage
from pydantic_core import to_json

from src.agents.prompt import read_prompt
from src.core.config import get_settings


@cache
def _template(path: Path) -> Template:
    """The prompt file at path as a Template, read once per path"""
    return Template(read_prompt(path))


@wrap_model_call
async def inject_document_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
) -> ModelCallResult:
    """Runs the model call with the state's document, if any, in a user message from
    inject_document_context.md just before the latest user message"""
    if not request.state.get("document"):
        return await handler(request)
    at = max(
        (
            index
            for index, message in enumerate(request.messages)
            if isinstance(message, HumanMessage)
        ),
        default=0,
    )
    return await handler(
        request.override(
            messages=[
                *request.messages[:at],
                HumanMessage(
                    _template(
                        get_settings().middleware_prompts / "inject_document_context.md"
                    ).substitute(document=to_json(request.state["document"]).decode())
                ),
                *request.messages[at:],
            ]
        )
    )
