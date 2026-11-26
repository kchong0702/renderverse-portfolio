from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clients.ezcareer import Step
from src.db.base import Base, EnumString, PydanticJson
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.conversations.enums import MessageRole, ServedAgent

if TYPE_CHECKING:
    from src.features.documents.models import DocumentChangeset


class AgentSession(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "agent"),
        CheckConstraint(
            "agent in ('career-director', 'career-consultant')", name="agent"
        ),
        CheckConstraint(
            "(agent = 'career-director') = (active_thread_id IS NOT NULL)",
            name="active_thread",
        ),
    )

    agent: Mapped[ServedAgent] = mapped_column(EnumString(ServedAgent))
    """The agent the surface sends its turns to"""

    active_thread_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "agent_threads.id",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        )
    )
    """career-director's thread new turns go on, which clearing replaces; None for
    career-consultant, whose threads are each a document's"""


class AgentThread(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "agent_threads"
    __table_args__ = (
        Index(
            "uq_agent_threads_document",
            "session_id",
            "document_id",
            unique=True,
            postgresql_where=text("cleared_at IS NULL"),
            sqlite_where=text("cleared_at IS NULL"),
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), index=True
    )
    """The session the thread belongs to"""

    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )
    """The document a career-consultant thread is about; None on career-director's"""

    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When the user cleared the conversation on it; None while new turns go on it"""


class ThreadMessageChangeset(UserScopedMixin, AuditMixin, Base):
    __tablename__ = "thread_message_changesets"

    message_id: Mapped[str] = mapped_column(
        ForeignKey("thread_messages.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    """The agent's message ending the turn that proposed the changeset"""

    changeset_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_changesets.id", ondelete="CASCADE"), primary_key=True
    )
    """The changeset the turn proposed"""


class ThreadMessage(UserScopedMixin, AuditMixin, Base):
    __tablename__ = "thread_messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'agent')", name="role"),
        CheckConstraint("role <> 'user' or timezone is not null", name="timezone"),
        CheckConstraint("role <> 'agent' or agent is not null", name="agent"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    """A user message's own id, or the id of the harness's message ending the
    turn"""

    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_threads.id", ondelete="CASCADE")
    )
    """The thread the message is on"""

    role: Mapped[MessageRole] = mapped_column(EnumString(MessageRole))
    """Who wrote it"""

    text: Mapped[str] = mapped_column(Text)
    """What the user wrote, or the agent's reply or question; empty when it had
    none"""

    timezone: Mapped[str | None] = mapped_column(String(64))
    """The IANA time zone the user wrote from; None on an agent's message"""

    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    """The document the message is about, if any"""

    agent: Mapped[str | None] = mapped_column(String(100))
    """The agent that answered; None on a user's message"""

    changesets: Mapped[list[DocumentChangeset]] = relationship(
        secondary=ThreadMessageChangeset.__table__,
        lazy="selectin",
        order_by="DocumentChangeset.created_at",
        viewonly=True,
    )
    """The changesets the agent proposed in the turn, the oldest first"""

    steps: Mapped[list[Step] | None] = mapped_column(
        PydanticJson(TypeAdapter(list[Step]))
    )
    """The steps the turn ran, as each last stood; None on a user's message"""

    failure: Mapped[str | None] = mapped_column(Text)
    """Why the turn failed or was stopped; None otherwise"""


Index(
    "ix_thread_messages_thread_id_created_at",
    ThreadMessage.thread_id,
    ThreadMessage.created_at.desc(),
    ThreadMessage.id.desc(),
)


__all__ = [
    "AgentSession",
    "AgentThread",
    "ThreadMessage",
    "ThreadMessageChangeset",
]
