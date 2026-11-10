from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InboxMessage(BaseModel):
    id: str
    """Gmail's message id"""

    thread_id: str
    """The Gmail conversation, for opening it in Gmail"""

    from_name: str
    """Who sent it, as their mail client names them; the address when unnamed"""

    from_email: str
    """The sender's address"""

    subject: str
    """The subject line"""

    snippet: str
    """The start of the body as plain text"""

    received_at: datetime
    """When Gmail received it"""

    unread: bool
    """Whether it is still unread in Gmail"""


class InboxMessageDetail(InboxMessage):
    to: str
    """The To header as sent"""

    body: str
    """The body as plain text; HTML-only mail is reduced to its text"""


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=20000)
    """The reply as plain text"""


class EmailCreate(ReplyCreate):
    to: str = Field(pattern=r"^[^@\s<>]+@[^@\s<>]+$", max_length=320)
    """The recipient's address"""

    subject: str = Field(min_length=1, max_length=500)
    """The subject line"""


__all__ = ["EmailCreate", "InboxMessage", "InboxMessageDetail", "ReplyCreate"]
