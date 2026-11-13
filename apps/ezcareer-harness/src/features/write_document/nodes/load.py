from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError

from src.core.errors import ExecuteError
from src.features.write_document.state import EditGraphState
from src.features.write_document.types import LoadedDocument
from src.shared.tool_error import ToolError


def load(state: EditGraphState) -> EditGraphState:
    """Loads the document the run edits through ops-api's document tool, with its
    PDF lines and files, failing the run with ops-api's reason when it can't"""
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
