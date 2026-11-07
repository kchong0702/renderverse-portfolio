from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from document_schema import AnyDocument, Changeset, Report

from src.shared.checks import CheckError
from src.shared.extraction import Line
from src.shared.tools import ProfileState


class EditState(ProfileState):
    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""


class EditGraphState(EditState, total=False):
    request: str
    """What the user asked for in chat"""

    errors: list[CheckError]
    """What the last check found wrong; empty when the changeset passed"""

    changeset: Changeset
    """The checked changeset with the page-fit edits, which goes to ops"""


@dataclass(frozen=True)
class EditContext:
    render: Callable[[AnyDocument], Awaitable[Report]]
    """Prints a document and returns how its pages came out"""


def sources(state: EditState) -> dict[str, str]:
    """The text of every PDF line and fact that edits may cite, by citation"""
    return {line.id: line.text for line in state["lines"]} | {
        f"fact:{fact.id}": fact.text for fact in state["facts"]
    }
