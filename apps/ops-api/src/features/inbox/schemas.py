from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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


__all__ = ["InboxMessage", "InboxMessageDetail"]
