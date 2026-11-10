from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Tokens(BaseModel):
    access_token: str
    """Short-lived token for the Gmail and Calendar APIs"""

    refresh_token: str | None = None
    """Offline token that mints new access tokens; only sent on a fresh consent"""

    scope: str = ""
    """Space-separated scopes the user granted"""


class GmailHeader(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    name: str
    """Header name, such as From"""

    value: str
    """Header value, already decoded by Gmail"""


class GmailBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    data: str = ""
    """The part's content, base64url encoded; empty for containers and attachments"""


class GmailPart(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

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


class GmailMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

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


class GmailThread(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    id: str
    """Gmail's thread id"""

    messages: list[GmailMessage]
    """The conversation's messages with their MIME trees, oldest first"""


class GmailSend(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    raw: str
    """The RFC 2822 message, base64url encoded"""

    thread_id: str | None = None
    """The conversation a reply joins; None starts a new one"""


class GmailSent(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    id: str
    """The sent message's id"""


class GmailProfile(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    email_address: str
    """The mailbox's address"""


class GmailRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    id: str
    """Gmail's message id"""


class GmailList(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    messages: list[GmailRef] = []
    """Matching messages, newest first; Gmail omits the key when there are none"""


class EventTime(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, extra="ignore", validate_by_name=True
    )

    date_time: datetime | None = None
    """Start or end of a timed event"""

    day: date | None = Field(default=None, alias="date")
    """Start or end of an all-day event; the end day is exclusive"""


class GoogleEvent(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    id: str
    """Calendar's event id"""

    status: str = "confirmed"
    """confirmed, tentative or cancelled"""

    transparency: str = "opaque"
    """opaque blocks the time; transparent shows the user as free"""

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


class EventList(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")

    time_zone: str = "UTC"
    """The calendar's time zone, such as Asia/Kuala_Lumpur"""

    items: list[GoogleEvent] = []
    """Events in the range, earliest first"""


class NewEvent(BaseModel):
    id: str | None = None
    """The event's id, base32hex; None lets Google pick one"""

    summary: str
    """The title"""

    start: EventTime
    """When it starts"""

    end: EventTime
    """When it ends"""

    description: str | None = None
    """Notes on the event; None leaves them empty"""

    location: str | None = None
    """Where it takes place; None leaves it empty"""


__all__ = [
    "EventList",
    "EventTime",
    "GmailList",
    "GmailMessage",
    "GmailPart",
    "GmailProfile",
    "GmailSend",
    "GmailSent",
    "GmailThread",
    "GoogleEvent",
    "NewEvent",
    "Tokens",
]
