from document_schema import Report, ResumeContent, ResumeDocument, TemplateId
from langchain_core.messages import AnyMessage
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.features.import_document.enums import Trait
from src.shared.extraction import Line, LineId


class ImportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    file: Base64Bytes
    """The uploaded PDF or Word file, base64 in JSON"""

    messages: list[AnyMessage] = Field(default_factory=list)
    """The user's note on how to import the résumé, if any"""


class ImportedResume(ResumeContent):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    skipped: list[LineId] = Field(default_factory=list)
    """Lines left out on purpose, such as page numbers"""


class LookSuggestion(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    template: TemplateId
    """The document-renderer template closest to the file's layout"""

    columns: int = Field(ge=1, le=2)
    """How many columns the file's pages are set in"""

    traits: list[Trait]
    """What else the file's layout has, which the template was picked by"""


class ImportResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    document: ResumeDocument
    """The draft, in the suggested template"""

    suggestion: LookSuggestion
    """The look the file's layout suggests"""

    pdf: str
    """The draft printed, as standard base64"""

    report: Report
    """How the draft's pages came out"""

    lines: list[Line]
    """The upload's text lines, which the draft's values cite"""
