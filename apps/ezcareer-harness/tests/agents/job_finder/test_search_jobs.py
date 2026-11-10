import json
from pathlib import Path

import httpx
import pytest
import respx
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, SecretStr

from src.adapters.job_sources import SearchResult, SourceUnavailable
from src.adapters.job_sources.jsearch import JSearchAdapter
from src.agents.job_finder.tools import search_jobs_tool
from src.core.config import reload_settings
from src.shared.factory import Factory
from src.shared.jobs import JobSearch, PostedWithin, Quota
from src.shared.profile import Preferences
from src.shared.run_context import RunContext

URL = "https://jsearch.p.rapidapi.com/search-v2"
RESPONSE = (Path(__file__).parent / "fixtures" / "jsearch_search.json").read_text()


def _page(count: int, cursor: str | None, start: int = 0) -> httpx.Response:
    template = json.loads(RESPONSE)["data"]["jobs"][0]
    jobs = [
        {**template, "job_id": f"job-{n}", "job_title": f"Engineer {n}"}
        for n in range(start, start + count)
    ]
    return httpx.Response(200, json={"data": {"jobs": jobs, "cursor": cursor}})


async def _search(
    tool: BaseTool,
    preferences: Preferences | None = None,
    search: JobSearch | None = None,
    context: RunContext | None = None,
    **args,
) -> ToolMessage:
    runtime = ToolRuntime(
        state={"preferences": preferences or Preferences(), "search": search},
        context=context,
        config={},
        stream_writer=lambda _: None,
        tool_call_id="1",
        store=None,
    )
    return await tool.ainvoke(
        {
            "type": "tool_call",
            "id": "1",
            "name": "search_jobs",
            "args": {**args, "runtime": runtime},
        }
    )


class _OtherQuery(BaseModel):
    query: str
    """Job title and key skills"""


class _DownSource:
    query = _OtherQuery
    """Its own arguments"""

    async def search(
        self,
        query: _OtherQuery,
        user_search: JobSearch | None,
        context: RunContext | None,
    ) -> SearchResult:
        """Can't search"""
        raise SourceUnavailable("other is down")


class _SalaryQuery(BaseModel):
    query: str
    """Job title and key skills"""

    min_salary: int | None = None
    """Lowest yearly salary"""


class _SalarySource(_DownSource):
    query = _SalaryQuery
    """Its own arguments"""


class _ClashQuery(BaseModel):
    query: int
    """Wrong type"""


class _ClashSource(_DownSource):
    query = _ClashQuery
    """Its own arguments"""


@pytest.fixture
def api_key(isolate_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EZCAREER_HARNESS_JSEARCH__API_KEY", "test-key")
    monkeypatch.setenv("EZCAREER_HARNESS_JSEARCH__RETRY_MAX_WAIT_SECONDS", "0")
    reload_settings()
    yield
    monkeypatch.undo()
    reload_settings()


@pytest.fixture
def search_jobs(api_key) -> BaseTool:
    return search_jobs_tool(Factory({"jsearch": JSearchAdapter}), ["jsearch"])


@respx.mock
async def test_returns_jobs_newest_first_with_duplicates_removed(search_jobs):
    respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(search_jobs, query="backend engineer python")

    assert [job.id for job in message.artifact.postings] == [
        "pQ7mN2_newest==",
        "aB3xK9_newer-copy==",
        "zZ1undated==",
    ]
    assert "aB3xK9_newer-copy==" in message.content
    assert "aB3xK9_older-copy==" not in message.content


@respx.mock
async def test_numbers_description_lines_and_keeps_posting_details(search_jobs):
    respx.get(URL).respond(200, text=RESPONSE)

    acme = (
        await _search(search_jobs, query="backend engineer python")
    ).artifact.postings[1]

    assert (acme.title, acme.company, acme.location, acme.country, acme.remote) == (
        "Senior Backend Engineer",
        "ACME",
        "London, GB",
        "GB",
        False,
    )
    assert acme.apply_url == "https://careers.acme.example/jobs/42"
    assert [(line.id, line.text) for line in acme.lines] == [
        (1, "Acme builds payment tools."),
        (2, "Requirements:"),
        (3, "- 5+ years of Python in production"),
        (4, "- Experience with FastAPI"),
        (5, "Nice to have: Kubernetes"),
    ]


@respx.mock
async def test_leaves_out_jobs_that_break_the_users_preferences(search_jobs):
    respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(
        search_jobs,
        Preferences(work_modes=["remote"], countries=["GB"]),
        query="backend engineer python",
    )

    assert [job.id for job in message.artifact.postings] == ["pQ7mN2_newest=="]
    assert "London" not in message.content


@respx.mock
async def test_sends_the_key_and_search_options(search_jobs):
    route = respx.get(URL).respond(200, text=RESPONSE)

    await _search(
        search_jobs,
        query="platform engineer",
        country="GB",
        remote_only=True,
        date_posted="month",
        employment_types=["FULLTIME", "CONTRACTOR"],
        job_requirements=["no_degree"],
        radius_km=25,
    )

    request = route.calls.last.request
    assert request.headers["X-RapidAPI-Key"] == "test-key"
    assert request.headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"
    assert dict(request.url.params) == {
        "query": "platform engineer",
        "country": "gb",
        "work_from_home": "true",
        "date_posted": "month",
        "employment_types": "FULLTIME,CONTRACTOR",
        "job_requirements": "no_degree",
        "radius": "25",
    }


@respx.mock
async def test_pages_by_cursor_until_it_has_thirty_jobs(search_jobs):
    pages = {None: _page(10, "2"), "2": _page(10, "3", 10), "3": _page(10, "4", 20)}
    route = respx.get(URL).mock(
        side_effect=lambda request: pages[request.url.params.get("cursor")]
    )

    message = await _search(search_jobs, query="backend engineer")

    assert route.call_count == 3
    assert len(message.artifact.postings) == 30


@respx.mock
async def test_fetches_one_page_when_asked_for_ten_jobs(search_jobs):
    route = respx.get(URL).mock(return_value=_page(10, "2"))

    message = await _search(search_jobs, query="backend engineer", max_jobs=10)

    assert route.call_count == 1
    assert len(message.artifact.postings) == 10


@respx.mock
async def test_stops_when_jsearch_has_no_more_pages(search_jobs):
    route = respx.get(URL).mock(return_value=_page(4, None))

    message = await _search(search_jobs, query="backend engineer")

    assert route.call_count == 1
    assert len(message.artifact.postings) == 4


@respx.mock
async def test_reads_the_quota_from_jsearchs_rate_limit_headers(search_jobs):
    respx.get(URL).respond(
        200,
        text=RESPONSE,
        headers={
            "x-ratelimit-requests-remaining": "42",
            "x-ratelimit-requests-limit": "200",
        },
    )

    message = await _search(search_jobs, query="backend engineer")

    assert json.loads(message.content)["requests_left"] == 42
    assert message.artifact.quota == Quota(remaining=42, limit=200)


@respx.mock
async def test_has_no_quota_when_jsearch_sends_no_rate_limit_headers(search_jobs):
    respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(search_jobs, query="backend engineer")

    assert json.loads(message.content)["requests_left"] is None
    assert message.artifact.quota is None


@respx.mock
async def test_the_users_search_replaces_the_agents_query_location_and_age(
    search_jobs,
):
    route = respx.get(URL).respond(200, text=RESPONSE)

    await _search(
        search_jobs,
        search=JobSearch(
            query="staff engineer",
            location="Manchester",
            posted_within=PostedWithin.DAY,
        ),
        query="backend engineer python in London",
        country="GB",
        date_posted="month",
    )

    params = route.calls.last.request.url.params
    assert params["query"] == "staff engineer in Manchester"
    assert params["date_posted"] == "today"
    assert params["country"] == "gb"


@respx.mock
async def test_fields_the_user_left_out_stay_the_agents(search_jobs):
    route = respx.get(URL).respond(200, text=RESPONSE)

    await _search(
        search_jobs,
        search=JobSearch(location="Leeds"),
        query="backend engineer",
        date_posted="month",
    )

    params = route.calls.last.request.url.params
    assert params["query"] == "backend engineer in Leeds"
    assert params["date_posted"] == "month"


@respx.mock
async def test_searches_on_the_runs_own_key_over_the_servers(search_jobs):
    route = respx.get(URL).respond(200, text=RESPONSE)

    await _search(
        search_jobs,
        context=RunContext(jsearch_api_key=SecretStr("user-key")),
        query="backend engineer",
    )

    assert route.calls.last.request.headers["X-RapidAPI-Key"] == "user-key"


@respx.mock
async def test_a_run_key_searches_when_the_server_has_none(isolate_env):
    reload_settings()
    route = respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(
        search_jobs_tool(Factory({"jsearch": JSearchAdapter}), ["jsearch"]),
        context=RunContext(jsearch_api_key=SecretStr("user-key")),
        query="backend engineer",
    )

    assert route.calls.last.request.headers["X-RapidAPI-Key"] == "user-key"
    assert len(message.artifact.postings) == 3


@respx.mock
async def test_retries_a_rate_limited_search(search_jobs):
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, json={"message": "Too many requests"}),
            httpx.Response(200, text=RESPONSE),
        ]
    )

    message = await _search(search_jobs, query="backend engineer python")

    assert route.call_count == 2
    assert len(message.artifact.postings) == 3


@respx.mock
async def test_tells_the_agent_when_jsearch_keeps_failing(search_jobs):
    route = respx.get(URL).respond(503)

    message = await _search(search_jobs, query="backend engineer python")

    assert route.call_count == 3
    assert message.status == "error"
    assert "JSearch answered 503" in message.text


@respx.mock
async def test_stops_calling_jsearch_after_three_failed_searches(search_jobs):
    route = respx.get(URL).respond(503)
    for _ in range(3):
        await _search(search_jobs, query="backend engineer python")
    calls = route.call_count

    message = await _search(search_jobs, query="backend engineer python")

    assert route.call_count == calls
    assert message.status == "error"
    assert "paused" in message.text


@respx.mock
async def test_a_bad_search_tells_the_agent_why_and_keeps_the_circuit_closed(
    search_jobs,
):
    reason = {"error": {"message": "Invalid date posted value.", "code": 400}}
    route = respx.get(URL).respond(400, json=reason)

    messages = [await _search(search_jobs, query="backend engineer") for _ in range(4)]

    assert route.call_count == 4
    assert "Invalid date posted value." in messages[-1].text


async def test_tells_the_agent_a_source_has_no_key(isolate_env):
    reload_settings()

    message = await _search(
        search_jobs_tool(Factory({"jsearch": JSearchAdapter}), ["jsearch"]),
        query="anything",
    )

    assert "JSEARCH__API_KEY is not set" in message.text


def test_the_model_reads_the_description_and_each_argument_once():
    tool = search_jobs_tool(Factory({"jsearch": JSearchAdapter}), ["jsearch"])
    definition = json.dumps(convert_to_openai_tool(tool))
    texts = [
        tool.description,
        *(field.description for field in tool.tool_call_schema.model_fields.values()),
    ]

    assert [definition.count(json.dumps(text)[1:-1]) for text in texts] == [1] * len(
        texts
    )


@respx.mock
async def test_one_unavailable_source_leaves_the_others_jobs(api_key):
    respx.get(URL).respond(200, text=RESPONSE)
    tool = search_jobs_tool(
        Factory({"jsearch": JSearchAdapter, "other": _DownSource}), ["jsearch", "other"]
    )

    message = await _search(tool, query="backend engineer python")

    assert len(message.artifact.postings) == 3
    assert json.loads(message.content)["failures"] == ["other is down"]


def test_sources_share_fields_named_alike():
    tool = search_jobs_tool(
        Factory({"jsearch": JSearchAdapter, "salary": _SalarySource}),
        ["jsearch", "salary"],
    )

    properties = tool.tool_call_schema.model_json_schema()["properties"]
    assert "min_salary" in properties
    assert list(properties).count("query") == 1


def test_sources_that_disagree_on_a_field_are_refused():
    with pytest.raises(ValueError, match="'query'"):
        search_jobs_tool(
            Factory({"jsearch": JSearchAdapter, "clash": _ClashSource}),
            ["jsearch", "clash"],
        )
