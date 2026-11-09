from document_schema import Changeset, FileHash

from src.agents.career_consultant import CareerConsultantState
from src.shared.checks import CheckError


class EditGraphState(CareerConsultantState, total=False):
    assets: dict[FileHash, bytes]
    """The bytes of every file the document uses"""

    errors: list[CheckError]
    """What the latest check found"""

    changeset: Changeset
    """The checked changeset with the page-fit deletes"""
