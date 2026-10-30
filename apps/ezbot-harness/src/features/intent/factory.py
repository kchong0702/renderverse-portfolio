from __future__ import annotations

from src.core.config import IntentSettings
from src.features.intent.classifier import DisabledIntentClassifier, IntentClassifier
from src.features.intent.laya import LayaIntentClassifier


def create_intent_classifier(settings: IntentSettings) -> IntentClassifier:
    """The configured intent classifier strategy"""
    if not settings.enabled:
        return DisabledIntentClassifier()
    return LayaIntentClassifier(settings)


__all__ = ["create_intent_classifier"]
