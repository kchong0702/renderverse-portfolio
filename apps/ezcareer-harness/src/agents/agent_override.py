from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs
from langchain_core.tools import BaseTool
from langgraph.config import get_config
from pydantic import BaseModel, ConfigDict


def current_override() -> "AgentOverride | None":
    """The agent override the current run's config carries, if any"""
    return get_config().get("configurable", {}).get("agent_override")


class AgentOverride(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    response_format: type[BaseModel] | None = None
    """The structured reply this call wants; one of the agent's response_formats"""

    tools: tuple[BaseTool, ...] = ()
    """Tools only this call gives the agent"""

    def config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """The run config that applies this override to a call of a shared agent"""
        return merge_configs({"configurable": {"agent_override": self}}, config)
