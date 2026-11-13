from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    GOOGLE = "google"
    """Gmail and Google Calendar, through an OAuth refresh token"""

    JSEARCH = "jsearch"
    """JSearch job search, through the user's RapidAPI key"""


__all__ = ["Provider"]
