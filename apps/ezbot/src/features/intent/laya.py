from __future__ import annotations

from collections.abc import Sequence

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.core.config import IntentSettings
from src.features.intent.classifier import IntentClassifier
from src.features.intent.models import Intent
from src.infrastructure.observability.logging import get_logger
from src.shared.enums import IntentType

_logger = get_logger(__name__)

_QUESTION = {
    "type": "choice",
    "instructions": (
        "Which part of Kelvin's portfolio does the user want to see right now, "
        "judging by their latest message?"
    ),
    "criteria": {
        IntentType.SKILLS: "Kelvin's technical skills: programming languages, frameworks, tech stack",
        IntentType.PROJECTS: "Kelvin's projects: portfolio work and things he has built",
        IntentType.ABOUT: "who Kelvin is: his background, biography, location, CV",
        IntentType.CONTACT: "how to reach Kelvin: email, LinkedIn, social media, hiring him",
        IntentType.NONE: "greetings, thanks, small talk, off-topic, or nothing to show",
    },
}


class LayaIntentClassifier(IntentClassifier):
    """Asks Laya the same question twice, about the latest message alone and
    about the recent conversation, then combines the two answers"""

    def __init__(
        self, settings: IntentSettings, client: httpx.AsyncClient | None = None
    ):
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=str(settings.url), timeout=httpx.Timeout(settings.timeout_s)
        )

    async def classify(self, messages: Sequence[BaseMessage]) -> Intent | None:
        turns = [
            m for m in messages if isinstance(m, (HumanMessage, AIMessage)) and m.text
        ]
        if not turns or not isinstance(turns[-1], HumanMessage):
            return None
        window = [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.text,
            }
            for m in turns[-self._settings.context :]
        ]
        payload = {
            "model": self._settings.model,
            "questions": {"intent": _QUESTION},
            "states": [turns[-1].text, window],
        }
        try:
            response = await self._client.post("/v1/systemone/batch", json=payload)
            response.raise_for_status()
            latest, conversation = (
                Intent(
                    intent_type=IntentType(r["answers"]["intent"]["choice"]),
                    confidence=float(r["answers"]["intent"]["answer_confidence"]),
                )
                for r in response.json()["results"]
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            _logger.warning("Intent classification failed: %r", exc)
            return None

        intent = self._combine(latest, conversation)
        _logger.info(
            "Intent classified",
            latest=latest.intent_type,
            latest_confidence=round(latest.confidence, 4),
            window=conversation.intent_type,
            window_confidence=round(conversation.confidence, 4),
            intent=intent.intent_type if intent else None,
        )
        return intent

    def _combine(self, latest: Intent, conversation: Intent) -> Intent | None:
        """The latest message alone handles topic switches and "thanks, bye",
        while the conversation resolves follow-ups like "show me". Trust the
        latest answer when it is confident, else the conversation's, and offer
        nothing below `threshold`."""
        if latest.confidence >= self._settings.latest_message_threshold:
            pick = latest
        else:
            pick = conversation
        if (
            pick.intent_type is IntentType.NONE
            or pick.confidence < self._settings.threshold
        ):
            return None
        return pick

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["LayaIntentClassifier"]
