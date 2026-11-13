import json
from importlib import import_module
from pathlib import Path

import pytest
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from src.agents.job_analyst.tools import search_jobs
from src.core.errors import ExecuteError
from src.shared.jobs import FoundJobs, JobSearch, PostedWithin, job_key
from src.shared.profile import Preferences

TOOL_MODULE = import_module("src.agents.job_analyst.tools.search_jobs")
OPS_API_FIXTURES = Path(__file__).parents[4] / "ops-api/tests/features/jobs/fixtures"
FOUND = json.loads((OPS_API_FIXTURES / "job_search_answer.json").read_text())
REQUEST = json.loads((OPS_API_FIXTURES / "job_search_request.json").read_text())


async def _search(search: JobSearch | None = None, **args) -> ToolMessage:
    """Calls search_jobs with args, the user's own search being search"""
    runtime = ToolRuntime(
        state={"preferences": Preferences(), "search": search},
        context=None,
        config={},
        stream_writer=lambda _: None,
        tool_call_id="1",
        store=None,
    )
    return await search_jobs.ainvoke(
        {
            "type": "tool_call",
            "id": "1",
            "name": "search_jobs",
            "args": {**args, "runtime": runtime},
        }
    )


@pytest.fixture
def ops_api(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """The data requests the run pauses with, each answered with FOUND"""
    asked: list[dict] = []

    def answer(request: dict) -> object:
        """FOUND, keeping the request"""
        asked.append(request)
        return FOUND

    monkeypatch.setattr(TOOL_MODULE, "interrupt", answer)
    return asked


def test_reads_the_answer_ops_api_sends_exactly_as_ops_api_serialises_it():
    assert FoundJobs.model_validate(FOUND).model_dump(mode="json") == FOUND


async def test_shows_the_agent_each_posting_under_a_short_id_and_keeps_its_own(
    ops_api,
):
    message = await _search(query="backend engineer python")

    assert json.loads(message.content) == FOUND | {
        "jobs": [job | {"id": job_key(job["id"])} for job in FOUND["jobs"]]
    }
    assert message.artifact == FoundJobs.model_validate(FOUND)


async def test_asks_ops_api_to_search_exactly_as_ops_api_reads_a_request(ops_api):
    await _search(
        query="platform engineer",
        location="London",
        country="GB",
        remote_only=True,
        posted_within="month",
        employment_types=["full_time", "contract"],
        job_requirements=["no_degree"],
        radius_km=25,
    )

    assert ops_api == [REQUEST]


async def test_the_users_search_replaces_the_agents_query_location_and_age(ops_api):
    await _search(
        search=JobSearch(
            query="staff engineer",
            location="Manchester",
            posted_within=PostedWithin.DAY,
        ),
        query="backend engineer python",
        location="London",
        country="GB",
        posted_within="month",
    )

    [asked] = ops_api
    assert (
        asked["query"],
        asked["location"],
        asked["posted_within"],
        asked["country"],
    ) == ("staff engineer", "Manchester", "day", "GB")


async def test_fields_the_user_left_empty_stay_the_agents(ops_api):
    await _search(
        search=JobSearch(query="", location=""),
        query="backend engineer",
        location="London",
    )

    [asked] = ops_api
    assert (asked["query"], asked["location"]) == ("backend engineer", "London")


async def test_fields_the_user_left_out_stay_the_agents(ops_api):
    await _search(
        search=JobSearch(location="Leeds"),
        query="backend engineer",
        posted_within=None,
    )

    [asked] = ops_api
    assert (asked["query"], asked["location"], asked["posted_within"]) == (
        "backend engineer",
        "Leeds",
        None,
    )


async def test_a_search_ops_api_cannot_run_reaches_the_agent_as_a_tool_error(
    monkeypatch,
):
    reason = "Connect JSearch in Settings to search for jobs"
    monkeypatch.setattr(TOOL_MODULE, "interrupt", lambda _: {"error": reason})

    message = await _search(query="anything")

    assert (message.status, message.content) == ("error", reason)


async def test_an_answer_that_is_not_a_job_search_fails_the_run(monkeypatch):
    monkeypatch.setattr(
        TOOL_MODULE,
        "interrupt",
        lambda _: {"jobs": "not a list", "requests_left": None},
    )

    with pytest.raises(ExecuteError, match="The job search didn't load"):
        await _search(query="anything")


def test_the_model_reads_the_description_and_each_argument_once():
    definition = json.dumps(convert_to_openai_tool(search_jobs))
    texts = [
        search_jobs.description,
        *(
            field.description
            for field in search_jobs.tool_call_schema.model_fields.values()
        ),
    ]

    assert [definition.count(json.dumps(text)[1:-1]) for text in texts] == [1] * len(
        texts
    )
