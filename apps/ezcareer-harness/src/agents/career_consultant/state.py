from typing import NotRequired

from document_schema import AnyDocument, Changeset, Report

from src.agents.state import ProfileState
from src.shared.extraction.types import Line


class CareerConsultantState(ProfileState):
    desired_document_id: str
    """The id of the résumé, CV or cover letter the agent works on"""

    document: NotRequired[AnyDocument]
    """The document as read_document or copy_for_job last read it; absent before"""

    actual_document_id: NotRequired[str]
    """The id of the document in document; absent before the first read"""

    report: NotRequired[Report]
    """How the document last printed; absent before its first render"""

    pdf_lines: NotRequired[list[Line]]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""

    changeset: NotRequired[Changeset]
    """The latest changeset the agent proposed that passed the checks, with the
    page-fit deletes"""
