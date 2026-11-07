from collections.abc import Awaitable, Callable
from typing import TypedDict

from document_schema import AnyDocument, Changeset, FileHash, Report
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.shared.checks import CheckError
from src.shared.extraction import Line
from src.shared.models import ProfileFact
from src.shared.tools import ProfileState


class EditState(ProfileState):
    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""


Render = Callable[[AnyDocument, dict[FileHash, bytes]], Awaitable[Report]]
"""Prints a document with the bytes of its files and returns how its pages came out"""


class EditInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    request: str
    """What the user asked for in chat"""

    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None = None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines, as the import returned them"""

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""

    assets: dict[FileHash, Base64Bytes] = Field(default_factory=dict)
    """The bytes of every file the document uses, for printing it"""


class EditOutput(TypedDict):
    changeset: Changeset
    """The checked changeset with the page-fit edits, which goes to ops"""


class EditGraphState(EditState, total=False):
    request: str
    """What the user asked for in chat"""

    assets: dict[FileHash, bytes]
    """The bytes of every file the document uses"""

    errors: list[CheckError]
    """What the last check found wrong; empty when the changeset passed"""

    changeset: Changeset
    """The checked changeset with the page-fit edits, which goes to ops"""


def sources(state: EditState) -> dict[str, str]:
    """The text of every PDF line and fact that edits may cite, by citation"""
    return {line.id: line.text for line in state["lines"]} | {
        f"fact:{fact.id}": fact.text for fact in state["facts"]
    }
