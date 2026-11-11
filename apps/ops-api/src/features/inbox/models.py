from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.inbox.enums import ThreadState


class EmailThread(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "email_threads"
    __table_args__ = (UniqueConstraint("user_id", "thread_id"),)

    thread_id: Mapped[str] = mapped_column(String(64))
    """Gmail's thread id"""

    last_message_id: Mapped[str] = mapped_column(String(64))
    """The thread's newest listed message when it was triaged; a newer one re-triages"""

    state: Mapped[ThreadState] = mapped_column(EnumString(ThreadState))
    """What the thread needs, as triage-email read it"""

    application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), default=None
    )
    """The application the thread is about, if any"""

    decide_by: Mapped[date | None] = mapped_column(default=None)
    """The deadline of an offer that names one"""

    interview_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the interview the thread confirms starts, in UTC"""

    interview_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When it ends, in UTC; None when the email does not say"""

    interview_location: Mapped[str | None] = mapped_column(String(500), default=None)
    """Where it takes place, such as a video link"""

    event_id: Mapped[str | None] = mapped_column(String(1024), default=None)
    """The Google Calendar event Ops added for the interview, so it adds it once"""


__all__ = ["EmailThread"]
