from document_schema import DocumentKind
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import FoundDocuments
from src.core.errors import ExecuteError


@tool
def find_documents(name: str | None = None, kind: DocumentKind | None = None) -> str:
    """Finds the user's résumés, CVs and cover letters by name, kind or both, best
    match first, each with the id edit_document takes"""
    try:
        found = FoundDocuments.model_validate(
            interrupt({"fetch": "documents", "name": name, "kind": kind})
        )
    except ValidationError as error:
        raise ExecuteError(f"The documents didn't load: {error}") from error
    return to_json(found.documents).decode()
