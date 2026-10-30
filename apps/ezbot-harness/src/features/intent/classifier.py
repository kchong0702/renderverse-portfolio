from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from langchain_core.messages import BaseMessage

from src.features.intent.models import Intent


class IntentClassifier(ABC):
    """Strategy for deciding which section the latest user message asks to see"""

    @abstractmethod
    async def classify(self, messages: Sequence[BaseMessage]) -> Intent | None:
        """Section to offer a button for, or None for no button"""

    async def aclose(self) -> None:
        """Release network resources"""


class DisabledIntentClassifier(IntentClassifier):
    """Used when intent detection is turned off: never offers a button"""

    async def classify(self, messages: Sequence[BaseMessage]) -> Intent | None:
        return None


__all__ = ["DisabledIntentClassifier", "IntentClassifier"]
