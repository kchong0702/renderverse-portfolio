from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """What the user asks the assistant"""


__all__ = ["ChatMessage"]
