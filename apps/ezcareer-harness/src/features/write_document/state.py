from document_schema import AnyDocument, Report

from src.shared.extraction import Line
from src.shared.tools import ProfileState


class EditState(ProfileState):
    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""


def sources(state: EditState) -> dict[str, str]:
    """The text of every PDF line and fact that edits may cite, by citation"""
    return {line.id: line.text for line in state["lines"]} | {
        f"fact:{fact.id}": fact.text for fact in state["facts"]
    }
