import json

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.core.config import IntentSettings
from src.features.intent.classifier import DisabledIntentClassifier
from src.features.intent.factory import create_intent_classifier
from src.features.intent.laya import LayaIntentClassifier
from src.shared.enums import IntentType


def laya_result(choice: str, confidence: float) -> dict:
    return {"answers": {"intent": {"choice": choice, "answer_confidence": confidence}}}


def make_classifier(handler, **settings) -> LayaIntentClassifier:
    settings = IntentSettings(enabled=True, url="http://laya", **settings)
    client = httpx.AsyncClient(
        base_url="http://laya", transport=httpx.MockTransport(handler)
    )
    return LayaIntentClassifier(settings, client)


def answering(latest: dict, window: dict):
    return lambda request: httpx.Response(200, json={"results": [latest, window]})


CONVERSATION = [
    HumanMessage("hi"),
    AIMessage("hello"),
    HumanMessage("what have you built?"),
    AIMessage("a 3D portfolio"),
    ToolMessage("tool output", tool_call_id="1"),
    HumanMessage("cool, show me"),
]


@pytest.mark.parametrize(
    ("latest", "window", "expected"),
    [
        (
            laya_result("contact", 0.9),
            laya_result("projects", 0.95),
            IntentType.CONTACT,
        ),
        (
            laya_result("contact", 0.4),
            laya_result("projects", 0.92),
            IntentType.PROJECTS,
        ),
        (laya_result("none", 0.85), laya_result("projects", 0.9), None),
        (laya_result("contact", 0.4), laya_result("projects", 0.3), None),
        (laya_result("contact", 0.4), laya_result("none", 0.9), None),
    ],
)
async def test_laya_trusts_a_confident_latest_answer_else_the_conversation(
    latest, window, expected
):
    intent = await make_classifier(answering(latest, window)).classify(CONVERSATION)

    assert (intent and intent.intent_type) == expected


async def test_laya_sends_the_latest_message_and_the_conversation_window():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return answering(laya_result("none", 1), laya_result("none", 1))(request)

    await make_classifier(handler, context=3).classify(CONVERSATION)

    body = requests[0]
    assert body["model"] == "multilingual"
    assert body["states"][0] == "cool, show me"
    assert body["states"][1] == [
        {"role": "user", "content": "what have you built?"},
        {"role": "assistant", "content": "a 3D portfolio"},
        {"role": "user", "content": "cool, show me"},
    ]
    assert set(body["questions"]["intent"]["criteria"]) == set(IntentType)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, json={"results": []}),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, json={"results": [laya_result("hobbies", 1)] * 2}),
    ],
)
async def test_laya_failures_mean_no_button(response):
    intent = await make_classifier(lambda request: response).classify(CONVERSATION)

    assert intent is None


async def test_laya_unreachable_means_no_button():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    assert await make_classifier(handler).classify(CONVERSATION) is None


async def test_disabled_intent_never_shows_a_button():
    classifier = create_intent_classifier(IntentSettings(enabled=False))

    assert isinstance(classifier, DisabledIntentClassifier)
    assert await classifier.classify(CONVERSATION) is None
