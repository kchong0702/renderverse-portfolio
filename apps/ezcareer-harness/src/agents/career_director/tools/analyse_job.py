from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, ValidationError, create_model
from pydantic_core import to_json

from src.agents.career_director.state import CareerDirectorState
from src.core.errors import ExecuteError
from src.shared.url import Url


async def _analyse_job(
    graph: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    url: Url,
) -> str:
    """Shows how well the job posting at a URL fits the user's profile, with every
    point cited"""
    try:
        output = await graph.ainvoke(
            graph.get_input_schema().model_validate(
                {
                    "url": url,
                    "facts": runtime.state["facts"],
                    "preferences": runtime.state["preferences"],
                }
            )
        )
    except (ValidationError, ExecuteError) as error:
        raise ToolException(str(error)) from error
    return to_json(output).decode()


def analyse_job_tool(graph: CompiledStateGraph) -> BaseTool:
    """analyse_job over graph, the analyse-job workflow"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_analyse_job, graph), _analyse_job),
        name="analyse_job",
        args_schema=create_model(
            "AnalyseJobArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerDirectorState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            url=(Url, Field(description="The job posting's URL")),
        ),
        handle_tool_error=True,
    )
