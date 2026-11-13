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


class RunTrigger(StrEnum):
    SCHEDULED = "scheduled"
    """Queued by the daily schedule at the user's run_at"""

    MANUAL = "manual"
    """Queued by the Find button"""

    AGENT = "agent"
    """Queued by the chat assistant, now or for later"""


class RunStatus(StrEnum):
    QUEUED = "queued"
    """Waiting for a worker; run_after says when it may start"""

    RUNNING = "running"
    """A worker holds it under its claim token until lease_until"""

    DONE = "done"
    """find-jobs ran and the jobs it found are stored"""

    FAILED = "failed"
    """Given up after the last attempt; error says why"""


class Match(StrEnum):
    MET = "met"
    """The profile shows it in full"""

    PARTLY = "partly"
    """The profile shows some of it"""

    NOT_MET = "not_met"
    """The profile does not show it"""


__all__ = ["Importance", "JobStatus", "Match", "RunStatus", "RunTrigger"]
