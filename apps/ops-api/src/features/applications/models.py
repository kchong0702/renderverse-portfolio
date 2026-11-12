from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, EnumString
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.applications.enums import (
    ApplicationStage,
    NextStepFormat,
    StepKind,
    StepStatus,
)
from src.features.jobs.models import Job


class Application(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "applications"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), unique=True)
    """The job it is for, which holds the company, role and fit"""

    job: Mapped[Job] = relationship(lazy="joined")
    """The job, loaded with the application"""

    stage: Mapped[ApplicationStage] = mapped_column(
        EnumString(ApplicationStage),
        default=ApplicationStage.DRAFT,
    )
    """Where it stands in the pipeline"""

    applied_on: Mapped[date | None] = mapped_column(default=None)
    """The day it was sent; None while a draft"""


class ApplicationStep(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "application_steps"
    __table_args__ = (
        CheckConstraint("starts_at is not null or due_on is not null", name="when"),
        CheckConstraint(
            "ends_at is null or (starts_at is not null and ends_at >= starts_at)",
            name="ends_after_start",
        ),
        CheckConstraint(
            "application_id is not null or email_thread_id is not null", name="owner"
        ),
    )

    application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, default=None
    )
    """The application it belongs to; None for a step found in an email thread
    about no tracked application"""

    kind: Mapped[StepKind] = mapped_column(EnumString(StepKind))
    """An interview, a follow-up, a take-home or an offer deadline"""

    title: Mapped[str] = mapped_column(String(200), default="")
    """What it is, such as Technical interview; empty to go by its kind"""

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When it starts; None for a step that only has a due day"""

    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When it ends, if known"""

    due_on: Mapped[date | None] = mapped_column(default=None)
    """The day it must be done by, such as a take-home's deadline"""

    format: Mapped[NextStepFormat | None] = mapped_column(
        EnumString(NextStepFormat), default=None
    )
    """Whether it is a video call, a phone call or on site"""

    location: Mapped[str | None] = mapped_column(String(500), default=None)
    """Where it happens, such as an address or a meeting link"""

    event_id: Mapped[str | None] = mapped_column(String(1024), default=None)
    """The Google Calendar event added for it"""

    email_thread_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_threads.id", ondelete="CASCADE"), index=True, default=None
    )
    """The email thread it came from, if any"""

    email_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """The start its email thread last gave; None when the thread gave none"""

    email_due_on: Mapped[date | None] = mapped_column(default=None)
    """The due day its email thread last gave; None when the thread gave none"""

    status: Mapped[StepStatus] = mapped_column(
        EnumString(StepStatus), default=StepStatus.OPEN
    )
    """Open, done or cancelled"""


__all__ = ["Application", "ApplicationStep"]
