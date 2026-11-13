from __future__ import annotations

from src.core.exceptions import InvalidInput


class UnreadableExport(InvalidInput):
    """The upload is not a profile export ops-api can read"""


__all__ = ["UnreadableExport"]
