from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, LargeBinary, String, Time, true
from sqlalchemy.orm import Mapped, mapped_column

from src.clients.ezcareer import ModelFamily
from src.db.base import Base
from src.db.mixins import AuditMixin


class UserSettings(AuditMixin, Base):
    """One row per user, created with the defaults on first read"""

    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    tailor_strong_matches: Mapped[bool] = mapped_column(default=True)
    follow_up_reminders: Mapped[bool] = mapped_column(default=True)
    suggest_replies: Mapped[bool] = mapped_column(default=True)
    add_interview_invites: Mapped[bool] = mapped_column(
        default=True, server_default=true()
    )
    offer_free_slots: Mapped[bool] = mapped_column(default=True, server_default=true())

    work_day_start: Mapped[time] = mapped_column(Time(), default=time(9, 0))
    work_day_end: Mapped[time] = mapped_column(Time(), default=time(18, 0))
    meeting_gap_minutes: Mapped[int] = mapped_column(default=30)

    ai_family: Mapped[ModelFamily | None] = mapped_column(String(20))
    """Provider of the chosen model; None until the user picks one"""

    ai_model: Mapped[str | None] = mapped_column(String(100))
    """The chosen model, one ezcareer-harness offers; set together with ai_family"""

    jsearch_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    """The user's JSearch API key, encrypted with Fernet under jsearch.encryption_key"""

    jsearch_quota_remaining: Mapped[int | None]
    """Searches left on the key, as the last find run read them"""

    jsearch_quota_limit: Mapped[int | None]
    """Searches the key allows, as the last find run read them"""


__all__ = ["UserSettings"]
