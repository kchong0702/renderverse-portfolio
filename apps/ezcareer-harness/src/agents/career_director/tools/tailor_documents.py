from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import DocumentsStarted
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail
from src.shared.tool_error import ToolError


@tool(response_format="content_and_artifact")
def tailor_documents(job_id: str) -> tuple[str, StepDetail]:
    """Copies the user's master résumé, and master cover letter when there is one, for a job on their Jobs page, by the
    id find_saved_jobs returned, and starts career-consultant tailoring each copy in the background; returns those started and skipped"""
    try:
        started = TypeAdapter(DocumentsStarted | ToolError).validate_python(
            interrupt({"execute_tool": "tailor_documents", "job_id": job_id})
        )
    except ValidationError as error:
        raise ExecuteError(f"The tailoring didn't start: {error}") from error
    if isinstance(started, ToolError):
        return f"No tailoring started: {started.error}", {}
    count = len(started.started)
    return to_json(started).decode(), {
        "step_detail": f"{count} documents" if count != 1 else "1 document"
    }
