from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter, computed_field
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.jobs.enums import Importance, JobStatus, Match


class Requirement(BaseModel):
    text: str = Field(min_length=1)
    """The requirement as the posting states it"""

    importance: Importance = Importance.REQUIRED
    """Whether the posting requires it or calls it nice to have"""

    match: Match
    """How well the profile meets it"""

    reason: str = ""
    """Why it is met, partly met or not met, in one sentence"""


class FitAnalysis(BaseModel):
    fit: int = Field(ge=0, le=100)
    """Fit score from 0 to 100, as analyse-job computes it"""

    requirements: list[Requirement] = Field(min_length=1)
    """Every requirement the posting states, mapped to the profile"""

    @computed_field
    @property
    def band(self) -> Literal["excellent", "good", "possible", "poor"]:
        """The fit score as a band, so the label always agrees with the score"""
        if self.fit >= 85:
            return "excellent"
        if self.fit >= 70:
            return "good"
        return "possible" if self.fit >= 50 else "poor"


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


__all__ = ["FitAnalysis", "Job", "Requirement"]
