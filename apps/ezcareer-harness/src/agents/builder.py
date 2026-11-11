from collections.abc import Mapping, Sequence
from functools import partial, reduce
from operator import or_

from deepagents import DeepAgentState, FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel

from src.agents.agent_override import tool_allowed
from src.agents.middlewares import (
    AllowedToolsMiddleware,
    HandoffToParentMiddleware,
    ResponseFormatMiddleware,
    dynamic_model_call,
)
from src.agents.registry import Agent
from src.clients.llm_providers import llm_provider


def _described(tool: BaseTool, descriptions: Mapping[str, str]) -> BaseTool:
    """tool with the agent profile's description, when the profile has one for it"""
    if tool.name in descriptions:
        return tool.model_copy(update={"description": descriptions[tool.name]})
    return tool


def _skill_tool(tools: Mapping[str, BaseTool], name: str, _: Runtime) -> list[BaseTool]:
    """The skill tool called name, unless the run's override leaves it out"""
    return [tools[name]] if name in tools and tool_allowed(name) else []


def build_agent(
    agent: Agent,
    *,
    response_formats: Sequence[type[BaseModel]] = (),
    tools: Sequence[BaseTool] = (),
    skill_tools: Sequence[BaseTool] = (),
    middleware: Sequence[AgentMiddleware] = (),
    state_schema: type[DeepAgentState] = DeepAgentState,
    context_schema: type | None = None,
    model: BaseChatModel | None = None,
) -> CompiledStateGraph:
    """Builds a registered agent as a read-only deep agent replying in any of
    response_formats, offered each of skill_tools once it reads a skill listing it"""
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=agent.skills, virtual_mode=True),
        routes={"/artifacts/": StateBackend()},
        artifacts_root="/artifacts",
    )
    descriptions = agent.profile.tool_description_overrides
    built = create_deep_agent(
        model=model or llm_provider(agent.family, agent.model),
        tools=[_described(tool, descriptions) for tool in tools],
        system_prompt=agent.system_prompt.read_text(),
        middleware=[
            FilesystemMiddleware(
                backend=backend, tools=["ls", "read_file", "glob", "grep"]
            ),
            *middleware,
            AllowedToolsMiddleware({tool.name for tool in (*tools, *skill_tools)}),
            HandoffToParentMiddleware(),
            ResponseFormatMiddleware(),
            dynamic_model_call,
            *(
                [
                    SkillsMiddleware(
                        backend=backend,
                        sources=["/"],
                        tools=partial(
                            _skill_tool,
                            {
                                tool.name: _described(tool, descriptions)
                                for tool in skill_tools
                            },
                        ),
                    )
                ]
                if agent.skills.is_dir()
                else []
            ),
        ],
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
