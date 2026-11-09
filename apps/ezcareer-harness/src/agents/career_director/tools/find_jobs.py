from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, ValidationError, create_model
from pydantic_core import to_json

from src.agents.career_director.state import CareerDirectorState
from src.core.errors import ExecuteError


async def _find_jobs(
    graph: CompiledStateGraph, runtime: ToolRuntime[None, CareerDirectorState]
) -> str:
    """Finds fresh jobs for the user's profile and preferences, ranked by fit"""
    try:
        output = await graph.ainvoke(
            graph.get_input_schema().model_validate(
                {
                    "facts": runtime.state["facts"],
                    "preferences": runtime.state["preferences"],
                }
            )
        )
    except (ValidationError, ExecuteError) as error:
        raise ToolException(str(error)) from error
    return to_json(output).decode()


def find_jobs_tool(graph: CompiledStateGraph) -> BaseTool:
    """find_jobs over graph, the find-jobs workflow"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_find_jobs, graph), _find_jobs),
        name="find_jobs",
        args_schema=create_model(
            "FindJobsArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerDirectorState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
        ),
        handle_tool_error=True,
    )
