from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, TextArray
from src.db.mixins import AuditMixin
from src.features.preferences.enums import SalaryPeriod


class JobPreferences(AuditMixin, Base):
    __tablename__ = "job_preferences"
    __table_args__ = (
        CheckConstraint(
            "work_modes <@ ARRAY['onsite', 'hybrid', 'remote']::text[]",
            name="work_modes",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "(min_salary_amount is null) = (min_salary_currency is null)"
            " and (min_salary_amount is null) = (min_salary_period is null)",
            name="min_salary",
        ),
        CheckConstraint("min_score between 0 and 100", name="min_score"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    """Whose preferences; one row per user, created with the defaults on first read"""

    target_roles: Mapped[str] = mapped_column(Text(), default="")
    """The roles the user is looking for, such as Backend engineer, Python"""

    location: Mapped[str] = mapped_column(String(200), default="")
    """Where the job search looks, such as Kuala Lumpur or remote"""

    countries: Mapped[list[str]] = mapped_column(TextArray, default=list)
    """ISO country codes the user wants to work in; empty accepts any"""

    visa_free_countries: Mapped[list[str]] = mapped_column(TextArray, default=list)
    """ISO country codes the user may work in without visa sponsorship"""

    work_modes: Mapped[list[str]] = mapped_column(TextArray, default=list)
    """WorkMode values the user accepts; empty accepts any"""

    min_salary_amount: Mapped[int | None] = mapped_column(default=None)
    """Lowest pay accepted, before tax; None when not set"""

    min_salary_currency: Mapped[str | None] = mapped_column(String(3), default=None)
    """ISO 4217 code of min_salary_amount"""

    min_salary_period: Mapped[SalaryPeriod | None] = mapped_column(
        EnumString(SalaryPeriod), default=None
    )
    """What min_salary_amount is paid for"""

    min_score: Mapped[int] = mapped_column(default=70)
    """Lowest fit score, 0 to 100, a found job must reach"""

    run_at: Mapped[time] = mapped_column(Time(), default=time(8, 0))
    """When the daily job search starts"""


__all__ = ["JobPreferences"]
