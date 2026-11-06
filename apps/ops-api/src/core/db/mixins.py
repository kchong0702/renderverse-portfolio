from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.actor import current_actor
from src.core.db.base import utcnow


class IdMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AuditMixin(TimestampMixin):
    """When and by whom a row was created and last changed; every feature table uses
    it, and tests fail on one without it. Only the latest change is kept, not a history.
    The *_by columns hold an actor string (see actor.py), filled in on insert and update.
    """

    created_by: Mapped[str] = mapped_column(String(100), default=current_actor)
    updated_by: Mapped[str] = mapped_column(
        String(100), default=current_actor, onupdate=current_actor
    )


class UserScopedMixin:
    """Every feature table belongs to one user; tests fail on a table without it"""

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


__all__ = ["AuditMixin", "IdMixin", "TimestampMixin", "UserScopedMixin"]
