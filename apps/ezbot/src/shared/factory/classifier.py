from __future__ import annotations

from src.core.agent.classifier.base import DisabledIntentClassifier, IntentClassifier
from src.core.agent.classifier.laya import LayaIntentClassifier
from src.core.config import IntentSettings


def create_intent_classifier(settings: IntentSettings) -> IntentClassifier:
    """The configured intent classifier strategy"""
    if not settings.enabled:
        return DisabledIntentClassifier()
    return LayaIntentClassifier(settings)


__all__ = ["create_intent_classifier"]
