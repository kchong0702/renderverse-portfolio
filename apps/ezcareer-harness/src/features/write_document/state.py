from document_schema import FileHash

from src.agents.career_consultant import CareerConsultantState


class EditGraphState(CareerConsultantState, total=False):
    document_id: str
    """The document the run edits"""

    assets: dict[FileHash, bytes]
    """The bytes of every file the document uses"""

    reply: str
    """The agent's answer to the user's message"""
