from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
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


__all__ = ["EmailThread"]
