from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """What the user asks the assistant"""

    document_id: UUID | None = None
    """The document open in the app; the agent reads it once documents land"""


__all__ = ["ChatMessage"]
