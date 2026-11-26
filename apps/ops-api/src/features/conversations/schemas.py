from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.clients.ezcareer import Step
from src.db.base import as_utc
from src.features.conversations.enums import MessageRole, ServedAgent
from src.features.profile.schemas import AgentProfile


class SessionRead(BaseModel):
    agent: ServedAgent
    """The agent the surface sends its turns to"""

    thread_id: UUID
    """The session's active thread"""


class MessageChangeset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    """The changeset's id"""

    document_id: UUID
    """The document its edits are for"""

    created_at: datetime
    """When the agent proposed it"""


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

    changesets: list[MessageChangeset]
    """The changesets the agent proposed in the turn, the oldest first"""

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


class ConsultantInput(AgentProfile):
    desired_document_id: UUID
    """The document the thread is about, which career-consultant works on"""


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


__all__ = [
    "ConsultantInput",
    "MessagePage",
    "MessageSend",
    "SessionRead",
    "SkippedTurn",
    "StartedTurn",
    "ThreadMessageRead",
]
