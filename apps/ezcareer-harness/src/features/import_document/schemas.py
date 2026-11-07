from document_schema import Report, ResumeDocument
from pydantic import BaseModel, ConfigDict

from src.shared.checks.check_error import CheckError
from src.shared.extraction import Line


class ImportResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    document: ResumeDocument
    """The draft, in the default template"""

    pdf: bytes
    """The draft printed"""

    report: Report
    """How the draft's pages came out"""

    lines: list[Line]
    """The upload's text lines, which the draft's values cite"""

    rounds: list[list[CheckError]]
    """The verifier's errors for each reply, empty for the one that passed"""

    config_version: str
    """Version of the ImportConfig the run used"""
