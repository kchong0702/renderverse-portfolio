from __future__ import annotations

from enum import StrEnum


class IntentType(StrEnum):
    SKILLS = "skills"
    """Kelvin's technical skills and tech stack"""

    PROJECTS = "projects"
    """Kelvin's projects and portfolio work"""

    ABOUT = "about"
    """Kelvin's background, biography and CV"""

    CONTACT = "contact"
    """How to reach or hire Kelvin"""

    NONE = "none"
    """Nothing to show: greetings, small talk, off-topic"""


__all__ = ["IntentType"]
