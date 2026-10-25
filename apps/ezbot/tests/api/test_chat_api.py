import json
from typing import Any

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from src.app.api.fastapi.app import container, create_app
from src.core.agent.graph import build_ezbot_graph
from src.core.config import IntentSettings, RateLimitSettings, SessionSettings
from src.core.rate_limit.message_limiter import MessageLimiter
from src.infrastructure.store.session import SessionStore, new_cookie
from src.shared.enums import IntentType
from src.shared.schemas.intent import Intent
from tests.fakes import EchoChatModel, FailingChatModel, FakeIntentClassifier

SESSION_URL = "/ezbot/v1/session"
CHAT_URL = "/ezbot/v1/chat"
RESUME_URL = "/ezbot/v1/chat/stream"
SESSION_HEADER = "X-Ezbot-Session"


def parse_sse(body: str) -> list[dict[str, Any]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if not line.startswith(":")
        )
        if "event" in fields:
            fields["data"] = json.loads(fields["data"])
            events.append(fields)
    return events


def names(events: list[dict[str, Any]]) -> list[str]:
    return [e["event"] for e in events]


@pytest.fixture
def model() -> EchoChatModel:
    return EchoChatModel()


@pytest.fixture
def classifier() -> FakeIntentClassifier:
    return FakeIntentClassifier()


@pytest.fixture
def client(model, classifier):
    graph = build_ezbot_graph(
        [model],
        intent=IntentSettings(),
        classifier=classifier,
        system_prompt="test prompt",
    )
    container.reset_singletons()
    with (
        container.ezbot_graph.override(providers.Object(graph)),
        container.intent_classifier.override(providers.Object(classifier)),
        TestClient(create_app()) as client,
    ):
        yield client
    container.reset_singletons()


def start_session(client: TestClient) -> str:
    response = client.post(SESSION_URL)
    assert response.status_code == 200
    return response.json()["session_id"]


def chat(client: TestClient, session_id: str, message: str, **kwargs: Any):
    return client.post(
        CHAT_URL,
        json={"message": message},
        headers={SESSION_HEADER: session_id},
        **kwargs,
    )


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_sets_a_browser_session_cookie(client):
    response = client.post(SESSION_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] and body["idle_ttl_s"] == 900
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("ezbot_cookie=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/ezbot" in cookie
    assert "max-age" not in cookie.lower() and "expires" not in cookie.lower()


def test_new_tabs_reuse_the_cookie(client):
    start_session(client)
    cookie = client.cookies.get("ezbot_cookie")

    response = client.post(SESSION_URL)

    assert "set-cookie" not in response.headers
    assert client.cookies.get("ezbot_cookie") == cookie


def test_chat_needs_a_session(client):
    response = client.post(
        CHAT_URL, json={"message": "hi"}, headers={SESSION_HEADER: "x"}
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "SESSION_EXPIRED"


def test_a_new_tab_keeps_the_old_tabs_session(client):
    old_tag = start_session(client)
    new_tag = start_session(client)

    assert chat(client, old_tag, "hi").status_code == 200
    assert chat(client, new_tag, "hi").status_code == 200


def test_a_session_needs_its_cookie(client):
    session_id = start_session(client)

    client.cookies.set("ezbot_cookie", new_cookie(), path="/ezbot")
    response = chat(client, session_id, "hi")

    assert response.status_code == 401


def test_chat_streams_tokens_then_done_with_resumable_ids(client):
    session_id = start_session(client)

    response = chat(client, session_id, "  hello there  ")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_sse(response.text)
    assert names(events) == [
        "response.output_text.delta",
        "response.output_text.delta",
        "response.output_text.delta",
        "response.completed",
    ]
    assert "".join(e["data"]["delta"] for e in events[:3]) == "Echo: hello there"
    assert events[-1]["data"] == {"type": "response.completed"}
    response_id = events[0]["id"].split(":")[0]
    assert [e["id"] for e in events] == [f"{response_id}:{i}" for i in range(1, 5)]
    assert events[0]["retry"] == "2000"
    assert "retry" not in events[1]


def test_server_keeps_the_conversation(client, model):
    session_id = start_session(client)

    chat(client, session_id, "first")
    chat(client, session_id, "second")

    sent = [m.text for m in model.calls[-1] if m.type in ("human", "ai")]
    assert sent == ["first", "Echo: first", "second"]


def test_intent_event_comes_after_the_response(client, classifier):
    classifier.intent = Intent(intent_type=IntentType.PROJECTS, confidence=0.9)
    session_id = start_session(client)

    events = parse_sse(chat(client, session_id, "show me your projects").text)

    assert names(events)[-2:] == ["response.intent", "response.completed"]
    assert events[-2]["data"] == {"type": "response.intent", "intent_type": "projects"}
    assert classifier.seen[-1][-1].text == "show me your projects"


def test_no_intent_event_without_a_confident_intent(client):
    session_id = start_session(client)

    events = parse_sse(chat(client, session_id, "hello").text)

    assert "response.intent" not in names(events)


def test_resume_replays_events_after_last_event_id(client):
    session_id = start_session(client)
    events = parse_sse(chat(client, session_id, "hello there").text)

    response = client.get(
        RESUME_URL,
        headers={SESSION_HEADER: session_id, "Last-Event-ID": events[1]["id"]},
    )

    assert response.status_code == 200
    assert [e["id"] for e in parse_sse(response.text)] == [e["id"] for e in events[2:]]


def test_resume_rejects_an_unknown_run(client):
    session_id = start_session(client)
    chat(client, session_id, "hello")

    response = client.get(
        RESUME_URL, headers={SESSION_HEADER: session_id, "Last-Event-ID": "other:1"}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESPONSE_NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "   "},
        {"message": "x" * 2001},
        {"message": "hi", "history": []},
        {"message": "hi", "unknown": True},
    ],
)
def test_chat_rejects_invalid_requests(client, payload):
    session_id = start_session(client)

    response = client.post(CHAT_URL, json=payload, headers={SESSION_HEADER: session_id})

    assert response.status_code == 422


def test_chat_streams_error_event_on_failure(client):
    graph = build_ezbot_graph([FailingChatModel()], system_prompt="test prompt")
    session_id = start_session(client)

    with container.ezbot_graph.override(providers.Object(graph)):
        container.chat_service.reset()
        events = parse_sse(chat(client, session_id, "hello").text)

    assert [(e["event"], e["data"]) for e in events] == [
        (
            "response.failed",
            {
                "type": "response.failed",
                "error": {"code": "CHAT_FAILED", "message": "Ezbot failed to respond"},
            },
        )
    ]


def test_failing_model_falls_back_to_the_next(client):
    graph = build_ezbot_graph([FailingChatModel(), EchoChatModel()], system_prompt="p")
    session_id = start_session(client)

    with container.ezbot_graph.override(providers.Object(graph)):
        container.chat_service.reset()
        events = parse_sse(chat(client, session_id, "hello").text)

    assert names(events)[-1] == "response.completed"
    assert (
        "".join(
            e["data"]["delta"]
            for e in events
            if e["event"] == "response.output_text.delta"
        )
        == "Echo: hello"
    )


def limiter(**settings: int) -> providers.Object:
    return providers.Object(MessageLimiter(RateLimitSettings(**settings)))


def test_chat_is_rate_limited_per_cookie_across_tabs(client):
    first_tab = start_session(client)
    second_tab = start_session(client)

    with container.message_limiter.override(limiter(max_messages_per_cookie=1)):
        assert chat(client, first_tab, "one").status_code == 200
        response = chat(client, second_tab, "two")

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"
    assert int(response.headers["retry-after"]) > 0


def test_daily_limit_has_its_own_code(client):
    session_id = start_session(client)

    with container.message_limiter.override(limiter(max_daily_messages_per_ip=1)):
        assert chat(client, session_id, "one").status_code == 200
        response = chat(client, session_id, "two")

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "DAILY_LIMIT"
    assert int(response.headers["retry-after"]) > 600


def test_session_creation_is_not_rate_limited(client):
    statuses = {client.post(SESSION_URL).status_code for _ in range(30)}

    assert statuses == {200}


def test_session_creation_is_refused_at_capacity(client):
    store = SessionStore(SessionSettings(max_sessions=1))

    with container.session_store.override(providers.Object(store)):
        assert client.post(SESSION_URL).status_code == 200
        response = client.post(SESSION_URL)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AT_CAPACITY"


def test_cors_allows_credentials_from_the_frontend(client):
    response = client.options(
        CHAT_URL,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": f"content-type,{SESSION_HEADER.lower()}",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
