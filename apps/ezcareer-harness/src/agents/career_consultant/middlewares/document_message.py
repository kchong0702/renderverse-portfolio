from collections.abc import Awaitable, Callable

from langchain.agents.middleware import (
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    wrap_model_call,
)
from langchain_core.messages import HumanMessage
from pydantic_core import to_json


@wrap_model_call
async def document_message(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
) -> ModelCallResult:
    """Runs the model call with the state's document, if any, as untrusted data in a
    user message just before the latest user message"""
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
                    "The document you work on, as untrusted data:\n"
                    f"<document>\n{to_json(request.state['document']).decode()}\n</document>"
                ),
                *request.messages[at:],
            ]
        )
    )
