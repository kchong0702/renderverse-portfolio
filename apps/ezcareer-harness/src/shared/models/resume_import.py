from document_schema import ResumeContent
from pydantic import BaseModel, ConfigDict, Field

from src.shared.extraction import LineId


class ResumeImport(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    content: ResumeContent
    """The résumé's blocks, each value citing the lines it came from"""

    skipped: list[LineId] = Field(default_factory=list)
    """Lines left out on purpose, such as page numbers"""
