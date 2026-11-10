from __future__ import annotations

from enum import StrEnum


class ImportStatus(StrEnum):
    PENDING = "pending"
    """Stored and waiting for ezcareer-harness's import-resume to read it"""

    RUNNING = "running"
    """import-resume is reading it now"""

    DONE = "done"
    """import-resume made the draft in document_id"""

    FAILED = "failed"
    """import-resume could not read the file; error says why"""


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


__all__ = ["ImportStatus", "LookTrait"]
