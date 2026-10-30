from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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


class Intent(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent_type: IntentType
    """Section the latest user message asks to see"""

    confidence: float
    """Classifier confidence in `intent_type`, from 0 to 1"""


__all__ = [
    "Intent",
    "IntentType",
]
