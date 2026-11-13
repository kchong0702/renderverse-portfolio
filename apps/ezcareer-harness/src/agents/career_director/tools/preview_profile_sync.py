from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import ProfileSyncPreview
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail
from src.shared.tool_error import ToolError


@tool(response_format="content_and_artifact")
def preview_profile_sync(document_id: str) -> tuple[str, StepDetail]:
    """Lists the edits that would bring the user's profile in line with one résumé or
    CV, by the id find_documents returned, and saves nothing"""
    try:
        preview = TypeAdapter(ProfileSyncPreview | ToolError).validate_python(
            interrupt({"execute_tool": "profile_sync", "document_id": document_id})
        )
    except ValidationError as error:
        raise ExecuteError(f"The profile sync didn't load: {error}") from error
    if isinstance(preview, ToolError):
        return f"The document can't be synced: {preview.error}", {}
    count = len(preview.edits)
    return to_json(preview.edits).decode(), {
        "step_detail": {0: "no changes", 1: "1 change"}.get(count, f"{count} changes")
    }
