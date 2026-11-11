from collections import Counter

from document_schema import DocumentKind
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import FoundDocuments
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail


@tool(response_format="content_and_artifact")
def find_documents(
    name: str | None = None, kind: DocumentKind | None = None
) -> tuple[str, StepDetail]:
    """Finds the user's résumés, CVs and cover letters by name, kind or both, best
    match first, each with the id edit_document takes"""
    try:
        found = FoundDocuments.model_validate(
            interrupt({"fetch": "documents", "name": name, "kind": kind})
        )
    except ValidationError as error:
        raise ExecuteError(f"The documents didn't load: {error}") from error
    words = {
        DocumentKind.RESUME: ("résumé", "résumés"),
        DocumentKind.CV: ("CV", "CVs"),
        DocumentKind.COVER_LETTER: ("cover letter", "cover letters"),
    }
    counts = Counter(document.kind for document in found.documents)
    return to_json(found.documents).decode(), {
        "step_detail": ", ".join(
            f"{count} {words[kind][count > 1]}" for kind, count in counts.items()
        )
        or "no documents"
    }
