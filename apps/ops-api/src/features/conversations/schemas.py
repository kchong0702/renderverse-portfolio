from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from document_schema import AnyDocument
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.clients.ezcareer import Step
from src.db.base import as_utc
from src.features.conversations.enums import MessageRole, ServedAgent
from src.features.imports import SourceLine
from src.features.profile.schemas import AgentProfile


class SessionRead(BaseModel):
    agent: ServedAgent
    """The agent the surface sends its turns to"""

    thread_id: UUID
    """The session's active thread"""


class ThreadMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    """The message's id, which paging goes back from"""

    role: MessageRole
    """Who wrote it"""

    text: str
    """What the user wrote, or the agent's reply or question"""

    created_at: Annotated[datetime, AfterValidator(as_utc)]
    """When it was written"""

    document_id: UUID | None
    """The document it is about, if any"""

    agent: str | None
    """The agent that answered; None on a user's message"""

    changeset_id: UUID | None
    """The changeset the agent proposed in the turn, if any"""

    steps: list[Step] | None
    """The steps the turn ran; None on a user's message"""

    failure: str | None
    """Why the turn failed or was stopped; None otherwise"""


class MessagePage(BaseModel):
    messages: list[ThreadMessageRead]
    """A page of the thread's messages, oldest first"""

    has_more: bool
    """Whether older messages are left"""


class MessageSend(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """What the user asks the agent"""


class DirectorInput(AgentProfile):
    active_agent: str | None = Field(default=None, exclude_if=lambda v: v is None)
    """The agent career-director last handed the thread to, while it answers it;
    None when career-director answered last"""

    document_id: UUID | None = Field(default=None, exclude_if=lambda v: v is None)
    """The document the thread's last answer was about, if any"""

    document: AnyDocument | None = Field(default=None, exclude_if=lambda v: v is None)
    """That document's current draft while career-consultant answers the thread"""

    pdf_lines: list[SourceLine] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """That document's imported lines while career-consultant answers the thread"""


class ConsultantInput(AgentProfile):
    document_id: UUID
    """The document the thread is about"""

    document: AnyDocument
    """Its current draft; its assets' bytes are not sent, as ops-api keeps none"""

    pdf_lines: list[SourceLine]
    """The imported file's lines; empty for a document not imported"""


class EditDocumentsRequest(BaseModel):
    execute_tool: Literal["edit_documents"]
    """career-director asks to start career-consultant on each document"""

    document_ids: list[UUID] = Field(min_length=1)
    """The documents to edit"""

    instruction: str = Field(min_length=1, max_length=4000)
    """What career-consultant is asked to do, sent as the user's message"""


class StartedTurn(BaseModel):
    document_id: UUID
    """The document a career-consultant turn now works on"""

    title: str
    """Its name in the documents list"""


class SkippedTurn(BaseModel):
    document_id: UUID
    """The document no turn was started on"""

    reason: str
    """Why not"""


class StartedTurns(BaseModel):
    started: list[StartedTurn]
    """The documents a career-consultant turn now works on in the background"""

    skipped: list[SkippedTurn]
    """The documents left alone, with why"""


__all__ = [
    "ConsultantInput",
    "DirectorInput",
    "EditDocumentsRequest",
    "MessagePage",
    "MessageSend",
    "SessionRead",
    "SkippedTurn",
    "StartedTurn",
    "StartedTurns",
    "ThreadMessageRead",
]
