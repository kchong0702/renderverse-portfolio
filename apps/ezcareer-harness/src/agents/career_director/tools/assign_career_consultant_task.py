from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.errors import GraphBubbleUp
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, create_model

from src.agents.career_director.state import CareerDirectorState
from src.shared.tool_artifact import StepDetail


async def _assign_career_consultant_task(
    agent: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    document_id: str,
    description: str,
) -> tuple[str, StepDetail]:
    """Has career-consultant do one task on one document and returns its final
    reply, with the document it worked on in the end"""
    try:
        result = await agent.ainvoke(
            {
                "messages": [HumanMessage(description)],
                "desired_document_id": document_id,
                "profile_facts": runtime.state["profile_facts"],
            }
        )
    except GraphBubbleUp:
        raise
    except Exception as error:
        raise ToolException(
            f"career-consultant stopped before finishing the task on document {document_id}, so treat it as not done"
        ) from error
    return result["messages"][-1].text, {
        "step_document_id": result.get("actual_document_id", document_id)
    }


def assign_career_consultant_task_tool(agent: CompiledStateGraph) -> BaseTool:
    """assign_career_consultant_task, which runs agent, career-consultant, as a sync
    subagent on one document"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_assign_career_consultant_task, agent),
            _assign_career_consultant_task,
        ),
        name="assign_career_consultant_task",
        args_schema=create_model(
            "AssignCareerConsultantTaskArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerDirectorState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            document_id=(
                str,
                Field(description="The document's id, as find_documents returned it"),
            ),
            description=(
                str,
                Field(
                    description="The complete task for this one document, which career-consultant gets as its only message"
                ),
            ),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
