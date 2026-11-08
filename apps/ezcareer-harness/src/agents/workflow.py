from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.config import get_config
from pydantic import BaseModel, ConfigDict


class Workflow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    response_format: type[BaseModel] | None = None
    """What the workflow wants back; the agent gets an answer tool with this as its arguments"""

    tools: tuple[BaseTool, ...] = ()
    """Tools only this workflow gives the agent"""

    strict: bool = True
    """Whether OpenAI models get the answer tool in strict mode; off for an
    answer schema strict mode refuses"""

    def config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """The run config that applies this workflow to a call of a shared agent"""
        config = config or {}
        return {
            **config,
            "configurable": {**config.get("configurable", {}), "workflow": self},
        }


def current_workflow() -> Workflow | None:
    """The workflow the current run's config names, if any"""
    return get_config().get("configurable", {}).get("workflow")
