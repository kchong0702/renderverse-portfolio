from collections.abc import Sequence

from deepagents import (
    DeepAgentState,
    FilesystemPermission,
    create_deep_agent,
    register_harness_profile,
)
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.pregel import Pregel

from src.agents.middlewares import WorkflowHook
from src.agents.registry import Agent
from src.clients.llm_providers import llm_provider


def build_agent(
    agent: Agent,
    *,
    tools: Sequence[BaseTool] = (),
    middleware: Sequence[AgentMiddleware] = (),
    state_schema: type[DeepAgentState] = DeepAgentState,
    context_schema: type | None = None,
    model: BaseChatModel | None = None,
) -> Pregel:
    """Builds a registered agent once as a deep agent with its skills read-only,
    under its model's harness profile; a Workflow in the run config gives a call
    its answer tool. model replaces the agent's own"""
    register_harness_profile(f"{agent.provider}:{agent.model}", agent.profile)
    built = create_deep_agent(
        model=model or llm_provider(agent.family, agent.model),
        tools=tools,
        system_prompt=agent.system_prompt.read_text(),
        middleware=[
            *middleware,
            WorkflowHook(agent.profile.tool_description_overrides),
        ],
        skills=["/"],
        permissions=[
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")
        ],
        backend=FilesystemBackend(root_dir=agent.skills, virtual_mode=True),
        state_schema=state_schema,
        context_schema=context_schema,
        name=agent.name,
    )
    return built.with_config(metadata={"agent": agent.name, "agent_hash": agent.hash})
