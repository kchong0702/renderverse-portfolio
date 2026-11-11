from zoneinfo import ZoneInfo

from document_schema import DocumentKind
from pydantic import BaseModel, ConfigDict

from src.shared.email import EmailThread, TimeSlot


class DocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """What edit_document takes to work on the document"""

    title: str
    """The name the user gave the document"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    master: bool
    """Whether it is the user's master document of its kind"""

    updated_at: str
    """When the user last changed it"""


class FoundDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    documents: list[DocumentSummary]
    """The documents that match, best match first"""


class FetchedThread(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    thread: EmailThread
    """The email thread draft_reply answers"""


class FreeSlots(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    free_slots: list[TimeSlot]
    """Times the user is free; empty when they offer none"""

    timezone: ZoneInfo
    """The user's time zone, such as Europe/London"""
