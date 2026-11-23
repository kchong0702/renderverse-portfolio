from typing import NotRequired

from document_schema import AnyDocument, Changeset, Report

from src.agents.state import ProfileState
from src.shared.extraction.types import Line


class CareerConsultantState(ProfileState):
    document_id: NotRequired[str]
    """The id of the résumé, CV or cover letter the agent works on"""

    document: AnyDocument
    """The résumé or letter as it is now"""

    report: NotRequired[Report | None]
    """How the document last printed; None before its first render"""

    lines: NotRequired[list[Line]]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""

    changeset: NotRequired[Changeset]
    """The latest changeset the agent proposed that passed the checks, with the
    page-fit deletes"""
