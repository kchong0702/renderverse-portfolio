from document_schema import ResumeContent
from pydantic import ConfigDict, Field

from src.shared.extraction import LineId


class ResumeImport(ResumeContent):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    skipped: list[LineId] = Field(default_factory=list)
    """Lines left out on purpose, such as page numbers"""
