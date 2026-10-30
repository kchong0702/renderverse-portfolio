import asyncio

import pytest
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from src.core.config import ChatSettings, IntentSettings, StreamSettings
from src.features.agent.graph import build_ezbot_graph
from src.features.chat.exceptions import ResponseInProgressError, ResponseNotFoundError
from src.features.chat.service import (
    ChatService,
    _storable,
)
from src.features.intent.models import Intent, IntentType
from src.features.session.models import Session
from tests.fakes import (
    BlockingChatModel,
    EchoChatModel,
    FakeIntentClassifier,
    ToolCallingChatModel,
)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_service(model, classifier=None, clock=None, **intent) -> ChatService:
    graph = build_ezbot_graph(
        [model],
        intent=IntentSettings(**intent),
        classifier=classifier or FakeIntentClassifier(),
        system_prompt="test prompt",
    )
    return ChatService(
        graph, ChatSettings(max_turns=2), StreamSettings(replay_ttl_s=60), clock=clock
    )


def make_session() -> Session:
    return Session(id="id", cookie="cookie", created_at=0, last_seen=0)


async def collect(response, after=0):
    return [event async for event in response.stream(after)]


async def test_stop_cancels_the_model_and_keeps_the_partial_response():
    model = BlockingChatModel(cancelled=asyncio.Event(), started=asyncio.Event())
    classifier = FakeIntentClassifier(
        Intent(intent_type=IntentType.SKILLS, confidence=1), 30
    )
    service = make_service(model, classifier)
    session = make_session()

    response = service.start(session, "hello")
    stream = response.stream()
    first = await asyncio.wait_for(anext(stream), timeout=5)
    assert service.stop(session)
    events = [first, *await asyncio.wait_for(collect(response, after=1), timeout=5)]

    await asyncio.wait_for(model.cancelled.wait(), timeout=5)
    assert [e.event for e in events] == [
        "response.output_text.delta",
        "response.cancelled",
    ]
    assert classifier.cancelled
    assert [m.text for m in session.history] == ["hello", "thinking"]


async def test_a_second_response_waits_for_the_first():
    model = BlockingChatModel(cancelled=asyncio.Event(), started=asyncio.Event())
    service = make_service(model)
    session = make_session()

    service.start(session, "hello")

    with pytest.raises(ResponseInProgressError):
        service.start(session, "again")
    service.stop(session)


async def test_a_finished_response_is_resumable_only_within_the_replay_ttl():
    clock = Clock()
    service = make_service(EchoChatModel(), clock=clock)
    session = make_session()

    response = service.start(session, "hello")
    events = await collect(response)
    resumed, after = service.resume(session, events[0].id)

    assert resumed is response and after == 1
    assert [e.id for e in await collect(resumed, after)] == [e.id for e in events[1:]]

    clock.now += 61
    with pytest.raises(ResponseNotFoundError):
        service.resume(session, events[0].id)


async def test_resume_without_last_event_id_replays_from_the_start():
    service = make_service(EchoChatModel())
    session = make_session()
    response = service.start(session, "hi")
    events = await collect(response)

    resumed, after = service.resume(session, None)

    assert after == 0 and len(await collect(resumed, after)) == len(events)


async def test_slow_intent_is_dropped_after_the_timeout():
    classifier = FakeIntentClassifier(
        Intent(intent_type=IntentType.ABOUT, confidence=1), 5
    )
    service = make_service(EchoChatModel(), classifier, timeout_s=0.05)
    session = make_session()

    events = await asyncio.wait_for(collect(service.start(session, "who?")), timeout=5)

    assert [e.event for e in events][-1] == "response.completed"
    assert "response.intent" not in [e.event for e in events]


async def test_classifier_sees_the_conversation_with_the_new_message():
    classifier = FakeIntentClassifier()
    service = make_service(EchoChatModel(), classifier)
    session = make_session()
    session.history = [HumanMessage("projects?"), AIMessage("A 3D portfolio.")]

    await collect(service.start(session, "show me"))

    assert [m.text for m in classifier.seen[-1]] == [
        "projects?",
        "A 3D portfolio.",
        "show me",
    ]


async def test_history_keeps_only_the_most_recent_turns():
    service = make_service(EchoChatModel())
    session = make_session()

    for message in ["one", "two", "three"]:
        await collect(service.start(session, message))

    assert [m.text for m in session.history] == [
        "two",
        "Echo: two",
        "three",
        "Echo: three",
    ]


async def test_a_message_without_a_response_is_a_turn_of_its_own():
    model = EchoChatModel()
    service = make_service(model)
    session = make_session()
    session.history = [
        HumanMessage("unanswered"),
        HumanMessage("one"),
        AIMessage("Echo: one"),
    ]

    await collect(service.start(session, "two"))

    sent = [m.text for m in model.calls[-1] if m.type in ("human", "ai")]
    assert sent == ["unanswered", "one", "Echo: one", "two"]
    assert [m.text for m in session.history] == [
        "one",
        "Echo: one",
        "two",
        "Echo: two",
    ]


@tool
def lookup() -> str:
    """Look up the portfolio"""
    return "a 3D portfolio"


def make_tool_service(model, **chat) -> ChatService:
    return ChatService(
        create_agent(model, tools=[lookup], system_prompt="test prompt"),
        ChatSettings(**chat),
        StreamSettings(),
    )


async def test_a_turn_keeps_its_tool_calls_and_results():
    model = ToolCallingChatModel(tool_name="lookup")
    service = make_tool_service(model)
    session = make_session()

    await collect(service.start(session, "projects?"))
    await collect(service.start(session, "more"))

    first_turn = session.history[:4]
    assert [type(m) for m in first_turn] == [
        HumanMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
    ]
    assert first_turn[1].tool_calls[0]["name"] == "lookup"
    assert first_turn[3].text == "Found: a 3D portfolio"
    _system_prompt, *sent = model.calls[2]
    assert sent[:4] == first_turn


async def test_trimming_drops_whole_turns_with_their_tool_messages():
    service = make_tool_service(ToolCallingChatModel(tool_name="lookup"), max_turns=1)
    session = make_session()

    await collect(service.start(session, "projects?"))
    await collect(service.start(session, "more"))

    assert [type(m) for m in session.history] == [
        HumanMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
    ]
    assert session.history[0].text == "more"


def test_storable_drops_unanswered_tool_calls_and_empty_replies():
    answered = AIMessage(content="", tool_calls=[{"name": "a", "args": {}, "id": "1"}])
    result = ToolMessage(content="ok", tool_call_id="1")
    unanswered = AIMessage(
        content="",
        tool_calls=[
            {"name": "a", "args": {}, "id": "2"},
            {"name": "b", "args": {}, "id": "3"},
        ],
    )
    partial_result = ToolMessage(content="half", tool_call_id="2")

    kept = _storable(
        [answered, result, unanswered, partial_result, AIMessage(content="")]
    )

    assert kept == [answered, result]


async def test_context_never_starts_on_a_response():
    model = EchoChatModel()
    service = make_service(model)
    session = make_session()
    session.history = [AIMessage("orphan"), HumanMessage("one"), AIMessage("Echo: one")]

    await collect(service.start(session, "two"))

    sent = [m.text for m in model.calls[-1] if m.type in ("human", "ai")]
    assert sent == ["one", "Echo: one", "two"]
