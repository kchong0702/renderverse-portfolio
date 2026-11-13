from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError

from src.agents.career_director.types import ProfileEdit, ProfileUpdated
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail, ToolArtifact
from src.shared.tool_error import ToolError


@tool(response_format="content_and_artifact")
def update_profile(
    edits: list[ProfileEdit], source: str = ""
) -> tuple[str, ToolArtifact | StepDetail]:
    """Saves edits to the user's profile, all or none, once the user approves them;
    source is the title of the document they come from, empty when the user asked"""
    try:
        updated = TypeAdapter(ProfileUpdated | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "profile_update",
                    "edits": [edit.model_dump(mode="json") for edit in edits],
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The profile didn't update: {error}") from error
    if isinstance(updated, ToolError):
        return f"Nothing was saved: {updated.error}", {}
    changes = f"{updated.saved} change{'' if updated.saved == 1 else 's'}"
    return f"Saved {changes} to the user's profile.", {
        "name": "profile_updated",
        "data": {"saved": updated.saved},
        "step_detail": changes,
    }
