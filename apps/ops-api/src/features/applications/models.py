from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.applications.enums import ApplicationStage


class Application(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "applications"

    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), default=None
    )
    """The stored posting it is for; its analysis gives the fit"""

    company: Mapped[str] = mapped_column(String(200))
    """Employer applied to"""

    role: Mapped[str] = mapped_column(String(200))
    """Job title applied for"""

    stage: Mapped[ApplicationStage] = mapped_column(
        EnumString(ApplicationStage),
        default=ApplicationStage.DRAFT,
    )
    """Where it stands in the pipeline"""

    applied_on: Mapped[date | None] = mapped_column(default=None)
    """The day it was sent; None while a draft"""

    next_step: Mapped[str] = mapped_column(String(200), default="")
    """What happens next, such as Technical interview or Follow up"""

    next_step_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the next step is due or booked"""


__all__ = ["Application"]
