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


class ImportSource(StrEnum):
    DATA = "data"
    """Uploaded on the Data page"""

    DOCUMENTS = "documents"
    """A résumé imported in Documents, which also made a document"""


class ChangeKind(StrEnum):
    FIELD = "field"
    """An import's value for a field that differs from the current one"""

    MATCH = "match"
    """An imported entry that may be the same as one already there"""


class ChangeChoice(StrEnum):
    CURRENT = "current"
    """Keep the field's current value"""

    CONFLICT = "conflict"
    """Take the import's value for the field"""

    SAME = "same"
    """The imported entry is the one already there"""

    DIFFERENT = "different"
    """The imported entry is another one; add it"""


__all__ = [
    "ChangeChoice",
    "ChangeKind",
    "EntryKind",
    "ImportSource",
    "SalaryPeriod",
    "WorkMode",
]
