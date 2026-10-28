from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.shared.enums import IntentType


class Intent(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent_type: IntentType
    """Section the latest user message asks to see"""

    confidence: float
    """Classifier confidence in `intent_type`, from 0 to 1"""


__all__ = ["Intent"]
