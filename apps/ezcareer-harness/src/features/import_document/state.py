from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from src.features.import_document.schemas import ResumeImport
from src.shared.extraction import Line


class ImportState(TypedDict, total=False):
    file: bytes
    """The uploaded PDF or Word file"""

    lines: list[Line]
    """The file's text lines"""

    structured_response: ResumeImport | None
    """The LLM's last reply; None when it held no ResumeImport"""

    messages: Annotated[list[AnyMessage], add_messages]
    """The user's note, if any"""
