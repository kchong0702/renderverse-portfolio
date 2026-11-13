from langchain_core.messages import AIMessage, ToolMessage

from tests.agents.career_director.test_handoffs import _graph, _turn
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

SCHEDULE = _call(
    "schedule_job_run",
    run_after="2026-11-13T08:00:00+08:00",
    search={"query": "Staff backend engineer"},
)


def _reports(result: dict, tool: str) -> list[ToolMessage]:
    return [
        m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == tool
    ]


async def test_a_run_is_queued_through_ops_api_without_approval():
    director = ScriptedChatModel(
        replies=[SCHEDULE, AIMessage("I'll search for staff roles tomorrow at 8.")]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Search for staff backend roles tomorrow at 8am",
        {"id": "run-1", "run_after": "2026-11-13T08:00:00+08:00"},
    )

    assert asked == [
        {
            "fetch": "job_run",
            "run_after": "2026-11-13T08:00:00+08:00",
            "search": {
                "query": "Staff backend engineer",
                "location": None,
                "posted_within": None,
            },
        }
    ]
    assert "schedule_job_run" in director.offered_tools[0]
    [report] = _reports(result, "schedule_job_run")
    assert report.text == "Queued a job search to run from Fri 13 Nov 08:00 +08:00."
    assert report.artifact == {"step_detail": "Fri 13 Nov 08:00 +08:00"}
    assert result["messages"][-1].text == "I'll search for staff roles tomorrow at 8."


async def test_a_run_ops_api_refuses_tells_the_director_nothing_was_queued():
    director = ScriptedChatModel(
        replies=[
            _call("schedule_job_run"),
            AIMessage("The job agent is already running."),
        ]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Run the job agent now",
        {"error": "The job agent is already running"},
    )

    assert asked == [{"fetch": "job_run", "run_after": None, "search": None}]
    [report] = _reports(result, "schedule_job_run")
    assert report.text == "No run was queued: The job agent is already running"
    assert report.artifact == {}


async def test_a_time_without_an_offset_is_refused_before_ops_api_is_asked():
    director = ScriptedChatModel(
        replies=[
            _call("schedule_job_run", run_after="2026-11-13T08:00:00"),
            AIMessage("Which time zone are you in?"),
        ]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])), "Search tomorrow at 8am"
    )

    assert asked == []
    [report] = _reports(result, "schedule_job_run")
    assert report.status == "error"
    assert "timezone" in report.text
