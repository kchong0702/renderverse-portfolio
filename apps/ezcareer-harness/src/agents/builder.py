from collections.abc import Sequence
from functools import reduce
from operator import or_

from deepagents import DeepAgentState, FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from src.agents.middlewares import (
    InjectToolsMiddleware,
    ResponseFormatMiddleware,
    dynamic_model_call,
)
from src.agents.registry import Agent
from src.clients.llm_providers import llm_provider


def build_agent(
    agent: Agent,
    *,
    response_formats: Sequence[type[BaseModel]] = (),
    tools: Sequence[BaseTool] = (),
    middleware: Sequence[AgentMiddleware] = (),
    state_schema: type[DeepAgentState] = DeepAgentState,
    context_schema: type | None = None,
    model: BaseChatModel | None = None,
) -> CompiledStateGraph:
    """Builds a registered agent as a deep agent that can only read its files and
    skills, able to reply in any of response_formats, on its run context's model"""
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=agent.skills, virtual_mode=True),
        routes={"/artifacts/": StateBackend()},
        artifacts_root="/artifacts",
    )
    built = create_deep_agent(
        model=model or llm_provider(agent.family, agent.model),
        tools=tools,
        system_prompt=agent.system_prompt.read_text(),
        middleware=[
            FilesystemMiddleware(
                backend=backend, tools=["ls", "read_file", "glob", "grep"]
            ),
            *middleware,
            InjectToolsMiddleware(agent.profile.tool_description_overrides),
            ResponseFormatMiddleware(),
            dynamic_model_call,
        ],
        skills=["/"],
        permissions=[
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")
        ],
        backend=backend,
        response_format=reduce(or_, response_formats) if response_formats else None,
        state_schema=state_schema,
        context_schema=context_schema,
        name=agent.name,
    )
    return built.with_config(metadata={"agent": agent.name, "agent_hash": agent.hash})
