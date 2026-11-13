from __future__ import annotations

from enum import StrEnum


class ImportSource(StrEnum):
    DATA = "data"
    """Uploaded on the Data page"""

    DOCUMENTS = "documents"
    """Uploaded in Documents as a résumé"""


class ImportStatus(StrEnum):
    QUEUED = "queued"
    """Waiting for a worker; run_after says when it may start"""

    PROCESSING = "processing"
    """A worker holds it under its claim token until lease_until"""

    DONE = "done"
    """Processed, with its results written"""

    FAILED = "failed"
    """Given up after the last attempt; error says why"""

    ABANDONED = "abandoned"
    """Superseded by a newer upload or cancelled before it was done"""


class LookTrait(StrEnum):
    ACCENT_BAND = "accent_band"
    """A coloured band down one side of the page"""

    PHOTO = "photo"
    """A photo on the first page"""

    TINTED_HEADINGS = "tinted_headings"
    """Headings on tinted strips"""

    RULED_HEADINGS = "ruled_headings"
    """Headings over or under a rule"""

    SERIF_FONT = "serif_font"
    """Body text in a serif font"""

    COLOURED_NAME = "coloured_name"
    """The name in a colour"""


__all__ = ["ImportSource", "ImportStatus", "LookTrait"]
