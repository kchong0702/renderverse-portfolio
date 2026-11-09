from document_schema import AnyDocument, Report

from src.agents.state import ProfileState
from src.shared.extraction.types import Line


class CareerConsultantState(ProfileState):
    document: AnyDocument
    """The résumé or letter as it is now"""

    report: Report | None
    """How the document last printed; None before its first render"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""
