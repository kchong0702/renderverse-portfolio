from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.jobs.enums import JobStatus, RunStatus, RunTrigger
from src.features.jobs.schemas import FitAnalysis, JobSearch


class Job(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("user_id", "external_id"),)

    external_id: Mapped[str | None] = mapped_column(String(200), default=None)
    """The posting's id at its source, such as a JSearch job id"""

    source: Mapped[str] = mapped_column(String(50), default="")
    """Where the posting was found, such as JSearch"""

    title: Mapped[str] = mapped_column(String(200))
    """Job title as posted"""

    company: Mapped[str] = mapped_column(String(200), default="")
    """Employer name"""

    location: Mapped[str] = mapped_column(String(200), default="")
    """Where the job is, such as Kuala Lumpur, hybrid"""

    salary: Mapped[str] = mapped_column(String(200), default="")
    """Pay as the posting states it; empty when not stated"""

    url: Mapped[str] = mapped_column(String(2000), default="")
    """Where to read the posting and apply"""

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the posting went up, if known"""

    status: Mapped[JobStatus] = mapped_column(
        EnumString(JobStatus),
        default=JobStatus.PICKED,
    )
    """Picked by the agent, saved or dismissed"""

    analysis: Mapped[FitAnalysis | None] = mapped_column(
        PydanticJson(TypeAdapter(FitAnalysis)), default=None
    )
    """How the posting fits the profile; None until analysed"""

    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the user first opened the job; None while it is new"""


class JobRun(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "job_runs"
    __table_args__ = (
        Index(
            "uq_job_runs_scheduled_day",
            "user_id",
            "scheduled_for",
            unique=True,
            postgresql_where=text("trigger = 'scheduled'"),
            sqlite_where=text("trigger = 'scheduled'"),
        ),
        Index(
            "uq_job_runs_running",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
        Index(
            "uq_job_runs_queued",
            "user_id",
            "trigger",
            unique=True,
            postgresql_where=text("status = 'queued'"),
            sqlite_where=text("status = 'queued'"),
        ),
    )

    trigger: Mapped[RunTrigger] = mapped_column(EnumString(RunTrigger))
    """What queued the run: the daily schedule, the Find button or the assistant"""

    scheduled_for: Mapped[date | None] = mapped_column(default=None)
    """The user's local date a scheduled run is for; one per day"""

    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    """The earliest a worker may claim it"""

    search: Mapped[JobSearch | None] = mapped_column(
        PydanticJson(TypeAdapter(JobSearch)), default=None
    )
    """The search the run hands find-jobs; None searches from the preferences"""

    status: Mapped[RunStatus] = mapped_column(
        EnumString(RunStatus), default=RunStatus.QUEUED
    )
    """How far the run has got"""

    claim_token: Mapped[UUID | None] = mapped_column(default=None)
    """The claim of the worker running it"""

    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the claim lapses unless the worker extends it"""

    attempts: Mapped[int] = mapped_column(default=0)
    """How many times it has been claimed"""

    error: Mapped[str] = mapped_column(Text(), default="")
    """Why the last attempt failed; empty otherwise"""

    found: Mapped[int] = mapped_column(default=0)
    """How many jobs find-jobs returned"""

    new: Mapped[int] = mapped_column(default=0)
    """How many of them were not stored before"""

    matched: Mapped[int] = mapped_column(default=0)
    """How many of them fit at or above the user's min_score"""

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When it was done or failed"""


__all__ = ["Job", "JobRun"]
