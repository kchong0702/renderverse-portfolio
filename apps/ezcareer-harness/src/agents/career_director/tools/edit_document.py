from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, ValidationError, create_model

from src.agents.career_director.state import CareerDirectorState
from src.core.errors import ExecuteError
from src.shared.tool_artifact import ToolArtifact


async def _edit_document(
    graph: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    document_id: str,
    request: str,
) -> tuple[str, ToolArtifact | None]:
    """Hands the user's request about one résumé, CV or cover letter to the edit
    flow, which replies and may propose a checked changeset for the user"""
    try:
        output = await graph.ainvoke(
            graph.get_input_schema().model_validate(
                {
                    "document_id": document_id,
                    "facts": runtime.state["facts"],
                    "messages": [HumanMessage(request)],
                }
            )
        )
    except (ValidationError, ExecuteError) as error:
        raise ToolException(str(error)) from error
    if output["changeset"] is None:
        return output["reply"], None
    return (
        (
            f"{output['reply']}\n\nEdits proposed: {len(output['changeset'].edits)}."
            " The user accepts or rejects each in the document."
        ),
        {
            "name": "changeset",
            "data": {
                "document_id": document_id,
                "changeset": output["changeset"].model_dump(mode="json"),
            },
        },
    )


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
            document_id=(
                str,
                Field(description="The document's id, as find_documents returned it"),
            ),
            request=(
                str,
                Field(description="What the user asked, in their own words"),
            ),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
