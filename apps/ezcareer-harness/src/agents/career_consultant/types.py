from document_schema import AnyDocument, Report
from pydantic import BaseModel, ConfigDict, Field

from src.shared.extraction.types import Line
from src.shared.profile import ProfileFact


class CareerConsultantInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    document: AnyDocument
    """The résumé or letter to talk about"""

    report: Report | None = None
    """How the document last printed; None before its first render"""

    lines: list[Line] = Field(default_factory=list)
    """The uploaded PDF's lines"""

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""
