from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import AuditMixin
from src.integrations.ezcareer import ModelFamily


class UserSettings(AuditMixin, Base):
    """One row per user, created with the defaults on first read"""

    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    job_query: Mapped[str] = mapped_column(String(200), default="")
    job_location: Mapped[str] = mapped_column(String(200), default="")
    job_agent_run_at: Mapped[time] = mapped_column(Time(), default=time(8, 0))
    job_min_score: Mapped[int] = mapped_column(default=70)

    tailor_strong_matches: Mapped[bool] = mapped_column(default=True)
    follow_up_reminders: Mapped[bool] = mapped_column(default=True)
    suggest_replies: Mapped[bool] = mapped_column(default=True)

    work_day_start: Mapped[time] = mapped_column(Time(), default=time(9, 0))
    work_day_end: Mapped[time] = mapped_column(Time(), default=time(18, 0))
    meeting_gap_minutes: Mapped[int] = mapped_column(default=30)

    ai_family: Mapped[ModelFamily | None] = mapped_column(String(20))
    """Provider of the chosen model; None until the user picks one"""

    ai_model: Mapped[str | None] = mapped_column(String(100))
    """The chosen model, one ezcareer-harness offers; set together with ai_family"""


__all__ = ["UserSettings"]
