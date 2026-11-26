import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.agents import build_agent
from src.agents.career_director import CareerDirectorState
from src.agents.career_director.tools import find_applications, find_saved_jobs
from src.app.container import Container
from src.shared.profile import Preferences
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

AGENT = Container().registry()["career-director"]
STAGES = {"draft": 0, "applied": 2, "replied": 0, "interview": 1, "offer": 0}
HARBOR = {
    "company": "Harbor Health",
    "role": "Software Engineer II",
    "stage": "interview",
    "applied_on": "2026-10-31",
    "fit": 82,
    "next_step": {
        "kind": "interview",
        "title": "Technical interview",
        "starts_at": "2026-11-20T02:00:00Z",
        "due_on": None,
        "format": "video",
        "location": "Google Meet",
    },
    "overdue": [],
}
SAVED = {
    "id": "job-kopi",
    "title": "Platform Engineer",
    "company": "Kopi Cloud",
    "location": "Kuala Lumpur",
    "salary": "",
    "url": "https://jobs.example.com/kopi",
    "posted_at": None,
    "status": "saved",
    "fit": 74,
}


async def _run(model: ScriptedChatModel, text: str, answer: object) -> tuple:
    """Runs career-director on text with only its read tools, answering its one
    pause; returns what the pause asked and the tool's report"""
    graph = build_agent(
        AGENT,
        tools=(find_applications, find_saved_jobs),
        state_schema=CareerDirectorState,
        model=model,
    ).copy(update={"checkpointer": InMemorySaver()})
    thread = {"configurable": {"thread_id": "t1"}}
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(text)],
            "profile_facts": [],
            "preferences": Preferences(),
        },
        thread,
    )
    [asked] = [i.value for i in result["__interrupt__"]]
    result = await graph.ainvoke(Command(resume=answer), thread)
    [report] = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    return asked, report


async def test_find_applications_gives_the_total_and_times_in_the_users_zone():
    model = ScriptedChatModel(
        replies=[_call("find_applications", stage="interview"), AIMessage("One.")]
    )

    asked, report = await _run(
        model,
        "Which applications are at interview?",
        {
            "by_stage": STAGES | {"closed": 1},
            "applications": [HARBOR],
            "timezone": "Asia/Kuala_Lumpur",
        },
    )

    assert asked == {
        "execute_tool": "applications",
        "company": None,
        "stage": "interview",
    }
    heading, found = report.text.split("\n", 1)
    assert heading == "Times are in Asia/Kuala_Lumpur."
    found = json.loads(found)
    assert found["total"] == 4
    assert found["by_stage"] == STAGES | {"closed": 1}
    assert found["applications"][0]["next_step"]["starts_at"] == (
        "2026-11-20T10:00:00+08:00"
    )
    assert report.artifact == {"step_detail": "1 application"}


async def test_find_saved_jobs_asks_for_the_company_and_gives_the_total():
    model = ScriptedChatModel(
        replies=[_call("find_saved_jobs", company="kopi"), AIMessage("One.")]
    )

    asked, report = await _run(
        model,
        "Did I save the Kopi job?",
        {"by_status": {"picked": 0, "saved": 1, "dismissed": 2}, "jobs": [SAVED]},
    )

    assert asked == {"execute_tool": "saved_jobs", "company": "kopi", "status": None}
    assert json.loads(report.text) == {
        "total": 3,
        "by_status": {"picked": 0, "saved": 1, "dismissed": 2},
        "jobs": [SAVED],
    }
    assert report.artifact == {"step_detail": "1 job"}
