from document_schema import Report, ResumeContent, ResumeDocument
from langchain_core.messages import AnyMessage
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.shared.extraction import Line, LineId


class ImportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    file: Base64Bytes
    """The uploaded PDF or Word file, base64 in JSON"""

    messages: list[AnyMessage] = Field(default_factory=list)
    """The user's note on how to import the résumé, if any"""


class ResumeImport(ResumeContent):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    skipped: list[LineId] = Field(default_factory=list)
    """Lines left out on purpose, such as page numbers"""


class ImportResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    document: ResumeDocument
    """The draft, in the default template"""

    pdf: str
    """The draft printed, as standard base64"""

    report: Report
    """How the draft's pages came out"""

    lines: list[Line]
    """The upload's text lines, which the draft's values cite"""
