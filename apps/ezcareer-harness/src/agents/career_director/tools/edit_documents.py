from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import DocumentsStarted
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail
from src.shared.tool_error import ToolError


@tool(response_format="content_and_artifact")
def edit_documents(document_ids: list[str], instruction: str) -> tuple[str, StepDetail]:
    """Starts career-consultant editing each document, by the ids find_documents returned, in the background, sending instruction
    unchanged as the user's message to each, so it must ask for one document's change on its own; returns those started and skipped"""
    try:
        started = TypeAdapter(DocumentsStarted | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "edit_documents",
                    "document_ids": document_ids,
                    "instruction": instruction,
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The edits didn't start: {error}") from error
    if isinstance(started, ToolError):
        return f"No edit started: {started.error}", {}
    count = len(started.started)
    return to_json(started).decode(), {
        "step_detail": f"{count} documents" if count != 1 else "1 document"
    }
