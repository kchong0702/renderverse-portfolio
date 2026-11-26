from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.errors import GraphBubbleUp
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, create_model

from src.agents.career_director.state import CareerDirectorState
from src.shared.tool_artifact import StepDetail


async def _assign_productivity_assistant_task(
    agent: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    description: str,
) -> tuple[str, StepDetail]:
    """Has productivity-assistant do one email or calendar task and returns its
    final reply"""
    try:
        result = await agent.ainvoke(
            {
                "messages": [HumanMessage(description)],
                "profile_facts": runtime.state["profile_facts"],
            }
        )
    except GraphBubbleUp:
        raise
    except Exception as error:
        raise ToolException(
            "productivity-assistant stopped before finishing this task, so treat it as not done"
        ) from error
    return result["messages"][-1].text, {"step_detail": "email"}


def assign_productivity_assistant_task_tool(agent: CompiledStateGraph) -> BaseTool:
    """assign_productivity_assistant_task, which runs agent, productivity-assistant,
    as a sync subagent"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_assign_productivity_assistant_task, agent),
            _assign_productivity_assistant_task,
        ),
        name="assign_productivity_assistant_task",
        args_schema=create_model(
            "AssignProductivityAssistantTaskArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerDirectorState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            description=(
                str,
                Field(
                    description="The complete email or calendar task, which productivity-assistant gets as its only message"
                ),
            ),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
