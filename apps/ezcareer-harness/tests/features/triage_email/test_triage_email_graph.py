from datetime import UTC, date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.app.app import create_app
from src.app.container import Container
from src.features.triage_email import build_graph
from src.features.triage_email.matching import matched_application
from src.features.triage_email.schemas import Application, Interview
from src.shared.email import EmailThread
from tests.conftest import ScriptedChatModel

THREAD = {
    "subject": "Your interview with Acme Payments",
    "messages": [
        {
            "sender": "Priya Shah <priya@talent.example>",
            "sent_at": "2026-11-09T09:12:00+00:00",
            "text": "Thanks for picking a time. See you Tuesday 11 Nov at 10:00 on Zoom.",
        }
    ],
}
APPLICATIONS = [
    {"id": "app-acme", "company": "Acme Payments", "role": "Backend Engineer"},
    {"id": "app-lumen", "company": "Lumen", "role": "Platform Engineer"},
]
START = "2026-11-11T10:00:00+00:00"


def _reading(**args: object) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "EmailReading", "args": args, "id": "call-reading"}],
    )


def _graph(model: ScriptedChatModel):
    return build_graph(Container().productivity_assistant.agent(model=model))


async def test_a_confirmed_interview_comes_out_with_its_time_and_application():
    model = ScriptedChatModel(
        replies=[
            _reading(
                state="interview",
                decide_by="2026-11-20",
                interview={
                    "start": START,
                    "end": "2026-11-11T10:45:00+00:00",
                    "format": "video",
                    "location": "Zoom",
                },
            )
        ]
    )

    result = await _graph(model).ainvoke(
        {"thread": THREAD, "applications": APPLICATIONS}
    )

    assert "handoff_to_parent" not in model.offered_tools[0]
    assert result == {
        "state": "interview",
        "application_id": "app-acme",
        "decide_by": None,
        "interview": Interview(
            start=datetime(2026, 11, 11, 10, tzinfo=UTC),
            end=datetime(2026, 11, 11, 10, 45, tzinfo=UTC),
            format="video",
            location="Zoom",
        ),
    }
    assert "<thread untrusted>" in model.requests[0][1].text
    assert "See you Tuesday" in model.requests[0][1].text
    assert "read_profile_facts" not in model.offered_tools[0]


async def test_an_offer_keeps_its_deadline_and_drops_any_interview():
    model = ScriptedChatModel(
        replies=[
            _reading(state="offer", decide_by="2026-11-20", interview={"start": START})
        ]
    )
    thread = THREAD | {"subject": "Offer: Platform Engineer at Lumen"}

    result = await _graph(model).ainvoke(
        {"thread": thread, "applications": APPLICATIONS}
    )

    assert (result["state"], result["decide_by"], result["interview"]) == (
        "offer",
        date(2026, 11, 20),
        None,
    )


async def test_an_answer_that_is_not_a_reading_goes_back_to_the_agent():
    model = ScriptedChatModel(
        replies=[AIMessage("It needs a reply."), _reading(state="needs_reply")]
    )

    result = await _graph(model).ainvoke({"thread": THREAD})

    assert result["state"] == "needs_reply"
    assert result["application_id"] is None
    assert "Reply with an EmailReading" in model.requests[-1][-1].text


def test_the_application_is_the_one_company_the_thread_names():
    thread = EmailThread.model_validate(THREAD)
    apps = [Application.model_validate(a) for a in APPLICATIONS]

    assert matched_application(thread, apps) == "app-acme"
    assert matched_application(thread, apps[1:]) is None


def test_several_named_companies_are_narrowed_by_role_or_left_unmatched():
    thread = EmailThread.model_validate(
        THREAD | {"subject": "Acme Payments and Lumen: Backend Engineer"}
    )
    apps = [Application.model_validate(a) for a in APPLICATIONS]
    lumen_backend = apps[1].model_copy(update={"role": "Backend Engineer"})

    assert matched_application(thread, apps) == "app-acme"
    assert matched_application(thread, [apps[0], lumen_backend]) is None


def test_triage_email_is_served_over_a2a():
    container = Container()
    container.productivity_assistant.agent(
        model=ScriptedChatModel(replies=[_reading(state="info")])
    )
    sent = datetime(2026, 11, 9, 9, 12, tzinfo=timezone(timedelta(hours=8)))

    response = TestClient(create_app(container)).post(
        "/ezcareer/a2a/triage-email",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m1",
                    "role": "ROLE_USER",
                    "parts": [
                        {
                            "data": {
                                "thread": THREAD
                                | {
                                    "messages": [
                                        THREAD["messages"][0]
                                        | {"sent_at": sent.isoformat()}
                                    ]
                                },
                                "applications": APPLICATIONS,
                            }
                        }
                    ],
                }
            },
        },
    )
    task = response.json()["result"]["task"]

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "triage-email"]
    assert reply["parts"][0]["data"] == {
        "state": "info",
        "application_id": "app-acme",
        "decide_by": None,
        "interview": None,
    }
