from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class GoogleJson(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")


class Tokens(BaseModel):
    access_token: str
    """Short-lived token for the Gmail and Calendar APIs"""

    refresh_token: str | None = None
    """Offline token that mints new access tokens; only sent on a fresh consent"""

    scope: str = ""
    """Space-separated scopes the user granted"""


class GmailHeader(GoogleJson):
    name: str
    """Header name, such as From"""

    value: str
    """Header value, already decoded by Gmail"""


class GmailBody(GoogleJson):
    data: str = ""
    """The part's content, base64url encoded; empty for containers and attachments"""


class GmailPart(GoogleJson):
    mime_type: str = ""
    """Content type, such as text/plain or multipart/alternative"""

    filename: str = ""
    """Set only on attachments"""

    headers: list[GmailHeader] = []
    """The part's headers; the top part carries the message headers"""

    body: GmailBody = GmailBody()
    """The part's own content"""

    parts: list[GmailPart] = []
    """Child parts of a multipart part"""

    def header(self, name: str) -> str:
        """The first header with this name, ignoring case; empty when absent"""
        return next(
            (h.value for h in self.headers if h.name.lower() == name.lower()), ""
        )

    def find(self, mime_type: str) -> str:
        """The first part of this type that is not an attachment, decoded"""
        if self.mime_type == mime_type and self.body.data and not self.filename:
            data = self.body.data + "=" * (-len(self.body.data) % 4)
            return urlsafe_b64decode(data).decode(errors="replace")
        return next((text for p in self.parts if (text := p.find(mime_type))), "")


class GmailMessage(GoogleJson):
    id: str
    """Gmail's message id"""

    thread_id: str
    """The conversation the message belongs to"""

    label_ids: list[str] = []
    """Gmail labels, such as UNREAD and INBOX"""

    snippet: str = ""
    """The start of the body, HTML-escaped"""

    internal_date: datetime
    """When Gmail received the message"""

    payload: GmailPart
    """Headers and the MIME tree"""


class GmailProfile(GoogleJson):
    email_address: str
    """The mailbox's address"""


class GmailRef(GoogleJson):
    id: str
    """Gmail's message id"""


class GmailList(GoogleJson):
    messages: list[GmailRef] = []
    """Matching messages, newest first; Gmail omits the key when there are none"""


class EventTime(GoogleJson):
    date_time: datetime | None = None
    """Start or end of a timed event"""

    day: date | None = Field(default=None, alias="date")
    """Start or end of an all-day event; the end day is exclusive"""


class GoogleEvent(GoogleJson):
    id: str
    """Calendar's event id"""

    status: str = "confirmed"
    """confirmed, tentative or cancelled"""

    summary: str = ""
    """The title; absent on events the user cannot see the details of"""

    location: str = ""
    """Where it takes place, as typed"""

    html_link: str = ""
    """The event in Google Calendar"""

    start: EventTime
    """When it starts"""

    end: EventTime
    """When it ends"""


class EventList(GoogleJson):
    items: list[GoogleEvent] = []
    """Events in the range, earliest first"""


__all__ = [
    "EventList",
    "EventTime",
    "GmailList",
    "GmailMessage",
    "GmailPart",
    "GmailProfile",
    "GoogleEvent",
    "Tokens",
]
