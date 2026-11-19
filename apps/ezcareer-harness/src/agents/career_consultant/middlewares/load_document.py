from langchain.agents.middleware import before_agent
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError

from src.agents.career_consultant.state import CareerConsultantState
from src.agents.career_consultant.types import LoadedDocument
from src.core.errors import ExecuteError
from src.shared.tool_error import ToolError


@before_agent(state_schema=CareerConsultantState)
def load_document(state: CareerConsultantState, runtime: Runtime) -> dict | None:
    """Loads the document state names through ops-api's document tool, with its PDF
    lines and files, at the start of every run; nothing when no document is named"""
    if "document_id" not in state:
        return None
    try:
        loaded = TypeAdapter(LoadedDocument | ToolError).validate_python(
            interrupt({"execute_tool": "document", "id": state["document_id"]})
        )
    except ValidationError as error:
        raise ExecuteError(f"The document didn't load: {error}") from error
    if isinstance(loaded, ToolError):
        raise ExecuteError(loaded.error)
    return {
        "document": loaded.document,
        "lines": loaded.lines,
        "assets": loaded.assets,
    }
