import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from src.app.container import Container
from src.core.errors import ExecuteError
from src.features.find_jobs import build_graph
from tests.agents.job_analyst.test_search_jobs import FOUND
from tests.conftest import ScriptedChatModel

INPUT = {
    "facts": [{"id": "py", "text": "Six years of Python in production"}],
    "preferences": {"countries": ["GB"]},
}


def _call(name: str, **args) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}]
    )


def _requirement(text: str, line: int, match: str) -> dict:
    return {
        "text": text,
        "importance": "required",
        "line_ids": [line],
        "match": match,
        "fact_ids": [] if match == "not_met" else ["fact:py"],
        "reason": "-",
    }


def _ranked(*jobs: tuple[str, list[dict]]) -> AIMessage:
    return _call("RankedJobs", jobs=[{"job_id": i, "requirements": r} for i, r in jobs])


PLATFORM = ("pQ7mN2_newest==", [_requirement("Terraform", 2, "not_met")])
BACKEND = (
    "aB3xK9_newer-copy==",
    [_requirement("5+ years of Python in production", 3, "met")],
)


async def _run(
    graph: CompiledStateGraph, data: dict, *answers: object
) -> tuple[list[object], dict]:
    """Runs find-jobs on data, answering each job search with the next of answers,
    then FOUND; returns what each pause asked and the output"""
    thread = {"configurable": {"thread_id": "find"}}
    result = await graph.ainvoke(data, thread)
    asked: list[object] = []
    while "__interrupt__" in result:
        asked += [i.value for i in result["__interrupt__"]]
        answer = answers[len(asked) - 1] if len(asked) <= len(answers) else FOUND
        result = await graph.ainvoke(Command(resume=answer), thread)
    return asked, result


async def test_unknown_jobs_go_back_and_the_ranking_comes_out_by_fit():
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("read_profile_facts"),
            _call("search_jobs", query="backend engineer python", country="GB"),
            _ranked(("made-up==", [_requirement("Python", 1, "met")]), PLATFORM),
            _ranked(PLATFORM, BACKEND),
        ]
    )

    container = Container()

    _, result = await _run(
        build_graph(container.job_analyst.agent(model=model), InMemorySaver()), INPUT
    )

    assert [(job.posting.id, job.fit) for job in result["jobs"]] == [
        ("aB3xK9_newer-copy==", 100),
        ("pQ7mN2_newest==", 0),
    ]
    assert result["jobs"][0].posting.apply_url == (
        "https://careers.acme.example/jobs/42"
    )
    assert "search_jobs" not in model.offered_tools[0]
    assert "search_jobs" in model.offered_tools[1]
    feedback = [m.text for m in model.requests[-1] if isinstance(m, HumanMessage)]
    assert '"GB"' in feedback[0]
    assert "unknown_job" in feedback[-1]


async def test_the_users_search_reaches_the_job_search_ops_api_runs():
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("search_jobs", query="backend engineer python", location="Leeds"),
            _ranked(BACKEND),
        ]
    )

    asked, result = await _run(
        build_graph(Container().job_analyst.agent(model=model), InMemorySaver()),
        INPUT
        | {
            "search": {
                "query": "platform engineer",
                "location": "Bristol",
                "posted_within": "month",
            }
        },
    )

    [search] = asked
    assert (
        search["execute_tool"],
        search["query"],
        search["location"],
        search["posted_within"],
    ) == ("job_search", "platform engineer", "Bristol", "month")
    assert [job.posting.id for job in result["jobs"]] == ["aB3xK9_newer-copy=="]
    assert '"location":"Bristol"' in model.requests[0][1].text


async def test_a_run_without_a_search_finds_nothing():
    model = ScriptedChatModel(replies=[_ranked()])

    asked, result = await _run(
        build_graph(Container().job_analyst.agent(model=model), InMemorySaver()),
        INPUT,
    )

    assert (asked, result) == ([], {"jobs": []})
    assert "My search" not in model.requests[0][1].text


async def test_a_failed_search_reaches_the_agent_and_the_jobs_found_before_stay():
    down = {"error": "JSearch did not answer"}
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("search_jobs", query="backend engineer python"),
            _call("search_jobs", query="platform engineer"),
            _ranked(BACKEND),
        ]
    )

    asked, result = await _run(
        build_graph(Container().job_analyst.agent(model=model), InMemorySaver()),
        INPUT,
        FOUND,
        down,
    )

    assert len(asked) == 2
    assert [job.posting.id for job in result["jobs"]] == ["aB3xK9_newer-copy=="]
    failed = [m for m in model.requests[-1] if isinstance(m, ToolMessage)][-1]
    assert (failed.status, failed.text) == ("error", "JSearch did not answer")


async def test_a_run_whose_every_search_failed_fails_with_why():
    reason = "Connect JSearch in Settings to search for jobs"
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("search_jobs", query="backend engineer python"),
            _ranked(),
        ]
    )

    with pytest.raises(ExecuteError, match=reason):
        await _run(
            build_graph(Container().job_analyst.agent(model=model), InMemorySaver()),
            INPUT,
            {"error": reason},
        )
