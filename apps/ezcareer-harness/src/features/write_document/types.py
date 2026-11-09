from typing import TypedDict

from document_schema import AnyDocument, Changeset, FileHash, Report
from langchain_core.messages import AnyMessage
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.shared.extraction.types import Line
from src.shared.profile import ProfileFact


class EditInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    messages: list[AnyMessage] = Field(min_length=1)
    """The user's chat, ending with their request"""

    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None = None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines"""

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""

    assets: dict[FileHash, Base64Bytes] = Field(default_factory=dict)
    """The bytes of every file the document uses"""


class EditOutput(TypedDict):
    changeset: Changeset
    """The checked changeset with the page-fit deletes"""
