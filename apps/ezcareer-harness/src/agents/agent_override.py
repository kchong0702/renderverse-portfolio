from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs
from langgraph.config import get_config
from pydantic import BaseModel, ConfigDict


def current_override() -> "AgentOverride | None":
    """The agent override the current run's config carries, if any"""
    return get_config().get("configurable", {}).get("agent_override")


def tool_allowed(name: str) -> bool:
    """Whether the current run's override lets the agent use its tool called name"""
    agent_override = current_override()
    return (
        agent_override is None
        or agent_override.tools is None
        or name in agent_override.tools
    )


class AgentOverride(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    response_format: type[BaseModel] | None = None
    """The structured reply this call wants; one of the agent's response_formats"""

    tools: frozenset[str] | None = None
    """Names of the agent's own tools this call may use; None allows them all"""

    def config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """The run config that applies this override to a call of a shared agent"""
        return merge_configs({"configurable": {"agent_override": self}}, config)
