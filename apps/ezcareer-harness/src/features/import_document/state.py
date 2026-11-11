from typing import Annotated, TypedDict

from document_schema import Report, ResumeDocument
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps

from src.features.import_document.schemas import LookSuggestion, ResumeImport
from src.shared.checks import CheckError
from src.shared.extraction import Line


class ImportState(TypedDict, total=False):
    file: bytes
    """The uploaded PDF or Word file"""

    lines: list[Line]
    """The file's text lines"""

    suggestion: LookSuggestion
    """The look the file's layout suggests"""

    structured_response: ResumeImport | None
    """The agent's last reply; None when it held no ResumeImport"""

    parsing_error: str | None
    """Why the last reply held no ResumeImport; None when it did"""

    errors: list[CheckError]
    """What the latest check found"""

    messages: Annotated[list[AnyMessage], add_messages]
    """The user's note, if any, then each failed check's request to fix its errors"""

    document: ResumeDocument
    """The draft, in the suggested template"""

    pdf: str
    """The draft printed, as standard base64"""

    report: Report
    """How the draft's pages came out"""

    remaining_steps: RemainingSteps
    """Graph steps left before the recursion limit"""
