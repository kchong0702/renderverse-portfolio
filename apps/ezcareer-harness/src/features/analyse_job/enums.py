from enum import StrEnum


class Importance(StrEnum):
    REQUIRED = "required"
    """The posting asks for it"""

    NICE_TO_HAVE = "nice_to_have"
    """The posting calls it a plus, preferred or bonus"""


class Match(StrEnum):
    MET = "met"
    """The profile shows it in full"""

    PARTLY = "partly"
    """The profile shows some of it"""

    NOT_MET = "not_met"
    """The profile does not show it"""


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
