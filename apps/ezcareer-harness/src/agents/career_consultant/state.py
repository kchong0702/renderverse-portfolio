from typing import NotRequired

from document_schema import AnyDocument, Changeset, FileHash, Report

from src.agents.state import ProfileState
from src.shared.extraction.types import Line


class CareerConsultantState(ProfileState):
    document_id: NotRequired[str]
    """The résumé, CV or cover letter the agent works on; load_document loads it"""

    document: NotRequired[AnyDocument]
    """The résumé or letter as it is now"""

    report: NotRequired[Report | None]
    """How the document last printed; None before its first render"""

    lines: NotRequired[list[Line]]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""

    assets: NotRequired[dict[FileHash, bytes]]
    """The bytes of every file the document uses, which printing needs"""

    changeset: NotRequired[Changeset]
    """The latest changeset the agent proposed that passed the checks, with the
    page-fit deletes"""
