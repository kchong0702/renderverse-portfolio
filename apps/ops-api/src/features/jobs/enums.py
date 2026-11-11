from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    PICKED = "picked"
    """Found by the job agent and not acted on yet"""

    SAVED = "saved"
    """Kept by the user to apply to"""

    DISMISSED = "dismissed"
    """Hidden by the user"""


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


__all__ = ["Importance", "JobStatus", "Match"]
