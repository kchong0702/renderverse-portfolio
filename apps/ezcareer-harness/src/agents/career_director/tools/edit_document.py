from functools import partial, update_wrapper

from document_schema import (
    AnyEdit,
    Delete,
    InsertBlock,
    InsertItem,
    Move,
    UpdateDesign,
    UpdateField,
    UpdateVisibility,
)
from langchain.tools import ToolRuntime
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model

from src.agents.career_director.state import CareerDirectorState
from src.agents.career_director.types import DocumentSummary
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail, ToolArtifact


def _title(messages: list[AnyMessage], document_id: str) -> StepDetail:
    """The document's title as find_documents last listed it, when it did"""
    titles = {
        document.id: document.title
        for message in messages
        if isinstance(message, ToolMessage)
        and message.name == "find_documents"
        and message.status == "success"
        for document in TypeAdapter(list[DocumentSummary]).validate_json(message.text)
    }
    return {"step_detail": titles[document_id]} if document_id in titles else {}


def _part(edit: AnyEdit) -> str:
    """The document path edit changes"""
    match edit:
        case UpdateField() | Move() | Delete():
            return edit.path
        case InsertItem():
            return edit.parent
        case InsertBlock():
            return f"blocks/{edit.block.id}"
        case UpdateVisibility():
            return f"blocks/{edit.block}"
        case UpdateDesign():
            return "design"


async def _edit_document(
    graph: CompiledStateGraph,
    runtime: ToolRuntime[None, CareerDirectorState],
    document_id: str,
    request: str,
) -> tuple[str, ToolArtifact | StepDetail]:
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
    detail = _title(runtime.state["messages"], document_id)
    if output["changeset"] is None:
        return output["reply"], detail
    return (
        (
            f"{output['reply']}\n\nEdits proposed: {len(output['changeset'].edits)}.\n"
            + "".join(
                f"- {edit.kind} {_part(edit)}\n" for edit in output["changeset"].edits
            )
            + "The user accepts or rejects each in the document."
        ),
        {
            "name": "changeset",
            "data": {
                "document_id": document_id,
                "changeset": output["changeset"].model_dump(mode="json"),
            },
            **detail,
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
