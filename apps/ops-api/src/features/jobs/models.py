from __future__ import annotations

from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.jobs.enums import JobStatus
from src.features.jobs.schemas import FitAnalysis


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


__all__ = ["Job"]
