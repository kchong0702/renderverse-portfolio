from collections.abc import Awaitable, Callable

from langchain.agents.middleware import (
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    wrap_model_call,
)

from src.shared.run_context import RunContext


@wrap_model_call
async def dynamic_model_call(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
) -> ModelCallResult:
    """Runs the model call on the run context's model, when the run has one"""
    context = request.runtime.context
    if isinstance(context, RunContext):
        return await handler(request.override(model=context.model))
    return await handler(request)
