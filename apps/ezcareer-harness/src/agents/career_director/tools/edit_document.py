from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, ValidationError, create_model
from pydantic_core import to_json

from src.agents.career_director.state import CareerDirectorState
from src.core.errors import ExecuteError


async def _edit_document(
    graph: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    request: str,
) -> str:
    """Proposes a checked changeset for a change to the open résumé or cover
    letter; it needs a document open"""
    try:
        output = await graph.ainvoke(
            graph.get_input_schema().model_validate(
                {
                    "messages": [HumanMessage(request)],
                    "document": runtime.state.get("document"),
                    "report": runtime.state.get("report"),
                    "lines": runtime.state.get("lines"),
                    "facts": runtime.state["facts"],
                }
            )
        )
    except (ValidationError, ExecuteError) as error:
        raise ToolException(str(error)) from error
    return to_json(output).decode()


def edit_document_tool(graph: CompiledStateGraph) -> BaseTool:
    """edit_document over graph, the edit-document workflow"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_edit_document, graph), _edit_document),
        name="edit_document",
        args_schema=create_model(
            "EditDocumentArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerDirectorState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            request=(
                str,
                Field(description="The change the user asked for, in their own words"),
            ),
        ),
        handle_tool_error=True,
    )
