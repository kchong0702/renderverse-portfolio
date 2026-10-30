from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, dynamic_prompt

from src.features.agent.prompt import PromptTemplate, load_prompt


def system_prompt_middleware(path: Path, **compile_values: Any) -> AgentMiddleware:
    """Renders a prompt file as the system prompt before every model call.

    The prompt is compiled once with `compile_values` bound. Each runtime
    variable is read from the agent state when a step has set it there,
    otherwise from the request context.
    """
    prompt = PromptTemplate(load_prompt(path), **compile_values)

    @dynamic_prompt
    def system_prompt(request: ModelRequest) -> str:
        context = request.runtime.context
        values = {
            name: request.state[name]
            if name in request.state
            else getattr(context, name)
            for name in prompt.runtime_variables
            if name in request.state or hasattr(context, name)
        }
        return prompt.render(values)

    return system_prompt


__all__ = ["system_prompt_middleware"]
