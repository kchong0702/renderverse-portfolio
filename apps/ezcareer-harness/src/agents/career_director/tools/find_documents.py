from collections import Counter

from document_schema import DocumentKind
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.state import CareerDirectorState
from src.agents.career_director.types import FoundDocuments
from src.core.errors import ExecuteError


@tool
def find_documents(
    runtime: ToolRuntime[None, CareerDirectorState],
    name: str | None = None,
    kind: DocumentKind | None = None,
) -> Command:
    """Finds the user's résumés, CVs and cover letters by name, kind or both, best
    match first, each with the id career-consultant works on; only the best match
    can be handed off"""
    try:
        found = FoundDocuments.model_validate(
            interrupt({"execute_tool": "documents", "name": name, "kind": kind})
        )
    except ValidationError as error:
        raise ExecuteError(f"The documents didn't load: {error}") from error
    words = {
        DocumentKind.RESUME: ("résumé", "résumés"),
        DocumentKind.CV: ("CV", "CVs"),
        DocumentKind.COVER_LETTER: ("cover letter", "cover letters"),
    }
    counts = Counter(document.kind for document in found.documents)
    return Command(
        update={
            **(
                {"found_documents": {found.documents[0].id: found.content}}
                if found.content and found.documents
                else {}
            ),
            "messages": [
                ToolMessage(
                    to_json(found.documents).decode(),
                    name="find_documents",
                    tool_call_id=runtime.tool_call_id,
                    artifact={
                        "step_detail": ", ".join(
                            f"{count} {words[kind][count > 1]}"
                            for kind, count in counts.items()
                        )
                        or "no documents"
                    },
                )
            ],
        }
    )
