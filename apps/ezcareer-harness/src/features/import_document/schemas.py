from base64 import b64encode
from typing import Annotated

from document_schema import Report, ResumeDocument
from pydantic import Base64Bytes, BaseModel, ConfigDict, PlainSerializer

from src.shared.checks.check_error import CheckError
from src.shared.extraction import Line


class ImportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    file: Base64Bytes
    """The uploaded PDF or Word file, base64 in JSON"""


class ImportResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    document: ResumeDocument
    """The draft, in the default template"""

    pdf: Annotated[
        bytes,
        PlainSerializer(
            lambda pdf: b64encode(pdf).decode(), return_type=str, when_used="json"
        ),
    ]
    """The draft printed, standard base64 in JSON"""

    report: Report
    """How the draft's pages came out"""

    lines: list[Line]
    """The upload's text lines, which the draft's values cite"""

    rounds: list[list[CheckError]]
    """The verifier's errors for each reply, empty for the one that passed"""

    config_hash: str
    """Hash of the ImportConfig the run used"""
