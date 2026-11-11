from __future__ import annotations

from enum import StrEnum


class ImportStatus(StrEnum):
    PENDING = "pending"
    """Stored and waiting for ezcareer-harness's import-resume, not wired in yet"""

    DONE = "done"
    """import-resume made the draft in document_id"""

    FAILED = "failed"
    """import-resume could not read the file; error says why"""


__all__ = ["ImportStatus"]
