from enum import StrEnum


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
