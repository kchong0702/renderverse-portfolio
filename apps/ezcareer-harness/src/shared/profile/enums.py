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


class FilterKind(StrEnum):
    YEARS = "years"
    """Years of experience overall"""

    WORK_MODE = "work_mode"
    """Onsite, hybrid or remote"""

    LOCATION = "location"
    """Countries the job is in"""

    WORK_AUTHORISATION = "work_authorisation"
    """Right to work without sponsorship"""

    SALARY = "salary"
    """Pay against the user's minimum"""
