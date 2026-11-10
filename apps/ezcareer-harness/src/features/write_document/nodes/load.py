from langgraph.types import interrupt
from pydantic import TypeAdapter, ValidationError

from src.core.errors import ExecuteError
from src.features.write_document.state import EditGraphState
from src.features.write_document.types import FetchedDocument, FetchFailed


def load(state: EditGraphState) -> EditGraphState:
    """Fetches the document the run edits from the client, with its PDF lines and
    files, failing the run with the client's reason when it can't send it"""
    try:
        fetched = TypeAdapter(FetchedDocument | FetchFailed).validate_python(
            interrupt({"fetch": "document", "id": state["document_id"]})
        )
    except ValidationError as error:
        raise ExecuteError(f"The document didn't load: {error}") from error
    if isinstance(fetched, FetchFailed):
        raise ExecuteError(fetched.error)
    return {
        "document": fetched.document,
        "lines": fetched.lines,
        "assets": fetched.assets,
    }
