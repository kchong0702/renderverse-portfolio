from __future__ import annotations

from enum import StrEnum


class EntryKind(StrEnum):
    ROLE = "role"
    """A job; its dates count towards years of experience"""

    EDUCATION = "education"
    """A degree, diploma or course"""

    PROJECT = "project"
    """Something the user built or led"""


class WorkMode(StrEnum):
    ONSITE = "onsite"
    """Works at the office"""

    HYBRID = "hybrid"
    """Splits time between office and home"""

    REMOTE = "remote"
    """Works from anywhere the employer allows"""


class SalaryPeriod(StrEnum):
    HOUR = "hour"
    """Paid per hour"""

    MONTH = "month"
    """Paid per month"""

    YEAR = "year"
    """Paid per year"""


__all__ = ["EntryKind", "SalaryPeriod", "WorkMode"]
