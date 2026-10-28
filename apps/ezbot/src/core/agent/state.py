from __future__ import annotations

from langgraph.graph import MessagesState

from src.shared.schemas.intent import Intent


class EzbotState(MessagesState):
    """The conversation, plus the intent classified alongside the response"""

    intent: Intent | None
    """Section to offer a button for, or None for no button"""


__all__ = ["EzbotState"]
