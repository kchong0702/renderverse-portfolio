from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.features.applications.enums import ApplicationStage
from src.features.calendar.schemas import Slot
from src.features.inbox.enums import ThreadState
from src.features.profile import ProfileFact


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

    state: ThreadState | None
    """What its thread needs, as triage-email read it; None until triaged"""

    decide_by: date | None
    """The deadline of an offer in its thread"""

    application_id: UUID | None
    """The application its thread is about"""

    on_calendar: bool
    """Whether Ops added the interview its thread confirms to Google Calendar"""


class InboxMessageDetail(InboxMessage):
    to: str
    """The To header as sent"""

    body: str
    """The body as plain text; HTML-only mail is reduced to its text"""


class InboxList(BaseModel):
    messages: list[InboxMessage]
    """The newest job-search emails, newest first"""

    needs_reply: int
    """How many of their threads wait on the user"""


class ThreadMessage(BaseModel):
    sender: str
    """Who sent it, as the From header names them"""

    sent_at: datetime
    """When Gmail received it"""

    text: str
    """The body as plain text"""


class ThreadContent(BaseModel):
    subject: str
    """The first message's subject line"""

    messages: list[ThreadMessage]
    """Every message, oldest first"""


class ThreadRequest(BaseModel):
    fetch: Literal["thread"]
    """A paused run asks for one of the user's email threads"""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    """The Gmail thread"""


class FreeSlotsRequest(BaseModel):
    fetch: Literal["free_slots"]
    """A paused run asks for the times the user is free"""

    days: int = Field(ge=1, le=30)
    """How many days from tomorrow to look in"""


class ThreadsRequest(BaseModel):
    fetch: Literal["threads"]
    """A paused run searches the user's email threads"""

    since: date | None = None
    """Earliest day a message was sent; None for any"""

    until: date | None = None
    """Latest day a message was sent; None for any"""

    keyword: str | None = Field(default=None, pattern=r'^[^"]{1,200}$')
    """Words the subject or a message contains; None for any"""

    sender: str | None = Field(default=None, pattern=r"^[\w .@+'&-]{1,200}$")
    """A sender's name, address or domain; None for anyone"""

    has_attachment: bool | None = None
    """Only threads with an attachment, or only those without; None for both"""

    limit: int = Field(ge=1)
    """The most threads to send back"""


class ThreadAnswer(BaseModel):
    thread: ThreadContent
    """The thread the run asked for"""


class ThreadSummary(BaseModel):
    id: str
    """The Gmail thread, which a thread request takes"""

    subject: str
    """The first message's subject line"""

    sender: str
    """Who sent the latest message, as the From header names them"""

    last_sent_at: datetime
    """When Gmail received the latest message"""

    message_count: int
    """How many messages the thread holds"""

    has_attachment: bool
    """Whether any of its messages carries an attachment"""


class ThreadsAnswer(BaseModel):
    threads: list[ThreadSummary]
    """The matching threads, newest first"""

    total: int
    """Gmail's estimate of how many threads match in all"""


class TriageApplication(BaseModel):
    id: UUID
    """The application's id, which triage-email names back"""

    company: str
    """Employer applied to"""

    role: str
    """Job title applied for"""


class TriageEmailInput(BaseModel):
    thread: ThreadContent
    """The thread to read"""

    applications: list[TriageApplication]
    """The user's applications the thread may be about"""


class Interview(BaseModel):
    start: datetime
    """When it starts"""

    end: datetime | None
    """When it ends, if the email says"""

    format: Literal["video", "phone", "on_site"] | None
    """How it takes place, if the email says"""

    location: str | None
    """Where, such as an address or a video link"""


class TriageEmailOutput(BaseModel):
    state: ThreadState
    """What the thread needs"""

    application_id: UUID | None
    """Which of the applications sent it is about"""

    decide_by: date | None
    """An offer's deadline"""

    interview: Interview | None
    """The interview the thread confirms"""


class DraftApplication(BaseModel):
    company: str
    """Employer applied to"""

    role: str
    """Job title applied for"""

    stage: ApplicationStage
    """Where it stands in the pipeline"""

    applied_at: date | None
    """The day it was sent"""


class DraftReplyInput(BaseModel):
    thread: ThreadContent | None
    """The email to answer; None writes a follow-up for the application"""

    application: DraftApplication | None
    """The application the email is about, or the one to follow up on"""

    free_slots: list[Slot]
    """Free time the draft may offer; empty offers none"""

    timezone: str
    """The time zone the slots are read in"""

    facts: list[ProfileFact]
    """What the user has done and knows"""


class DraftReplyOutput(BaseModel):
    body: str
    """The plain-text email"""

    slots: list[Slot]
    """The free slots it offers, empty when the email does not ask for times"""


class FollowUpDraft(BaseModel):
    body: str
    """The plain-text follow-up email"""


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=20000)
    """The reply as plain text"""


class EmailCreate(ReplyCreate):
    to: str = Field(pattern=r"^[^@\s<>]+@[^@\s<>]+$", max_length=320)
    """The recipient's address"""

    subject: str = Field(min_length=1, max_length=500)
    """The subject line"""


__all__ = [
    "DraftApplication",
    "DraftReplyInput",
    "DraftReplyOutput",
    "EmailCreate",
    "FollowUpDraft",
    "FreeSlotsRequest",
    "InboxList",
    "InboxMessage",
    "InboxMessageDetail",
    "ReplyCreate",
    "ThreadAnswer",
    "ThreadContent",
    "ThreadMessage",
    "ThreadRequest",
    "ThreadSummary",
    "ThreadsAnswer",
    "ThreadsRequest",
    "TriageApplication",
    "TriageEmailInput",
    "TriageEmailOutput",
]
