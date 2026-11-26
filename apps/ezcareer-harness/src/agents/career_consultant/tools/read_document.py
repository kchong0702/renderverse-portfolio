from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json

from src.agents.career_consultant.state import CareerConsultantState
from src.agents.career_consultant.types import DocumentDraft
from src.core.errors import ExecuteError
from src.shared.tool_error import ToolError


@tool
def read_document(runtime: ToolRuntime[None, CareerConsultantState]) -> Command | str:
    """Reads the document you work on as it is now, with its PDF's lines and the job it
    is a copy for; read it before you edit it and again before each new proposal"""
    try:
        draft = TypeAdapter(DocumentDraft | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "read_document",
                    "document_id": runtime.state["document_id"],
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The document didn't load: {error}") from error
    if isinstance(draft, ToolError):
        return f"The document didn't load: {draft.error}"
    return Command(
        update={
            "document": draft.document,
            "document_read_for": runtime.state["document_id"],
            "document_title": draft.title,
            "pdf_lines": draft.pdf_lines,
            "messages": [
                ToolMessage(
                    "<document untrusted>\n"
                    + to_json(
                        draft,
                        include={
                            "document": True,
                            "pdf_lines": {"__all__": {"id", "text"}},
                            "job_id": True,
                        },
                    ).decode()
                    + "\n</document>",
                    name="read_document",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
