from document_schema import DocumentKind
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic_core import to_json

from src.agents.career_director.types import FoundDocuments


@tool
def find_documents(name: str | None = None, kind: DocumentKind | None = None) -> str:
    """Finds the user's résumés, CVs and cover letters by name, kind or both, best
    match first, each with the id edit_document takes"""
    return to_json(
        FoundDocuments.model_validate(
            interrupt({"fetch": "documents", "name": name, "kind": kind})
        ).documents
    ).decode()
