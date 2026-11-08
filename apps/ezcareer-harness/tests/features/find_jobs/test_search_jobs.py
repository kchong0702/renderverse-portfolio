import json
from pathlib import Path

import httpx
import pytest
import respx
from langchain.tools import ToolRuntime
from langchain_core.utils.function_calling import convert_to_openai_tool

from src.core.config import reload_settings
from src.features.find_jobs.sources import jsearch
from src.features.find_jobs.tools import search_jobs
from src.shared.models import Preferences

URL = "https://jsearch.p.rapidapi.com/search-v2"
RESPONSE = (Path(__file__).parent / "fixtures" / "jsearch_search.json").read_text()


@pytest.fixture
def api_key(isolate_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EZCAREER_HARNESS_JSEARCH__API_KEY", "test-key")
    reload_settings()
    yield
    monkeypatch.undo()
    reload_settings()


async def _search(preferences: Preferences | None = None, **args):
    runtime = ToolRuntime(
        state={"preferences": preferences or Preferences()},
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


@respx.mock
async def test_returns_jobs_newest_first_with_duplicates_removed(api_key):
    respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(query="backend engineer python")

    assert [job.id for job in message.artifact] == [
        "pQ7mN2_newest==",
        "aB3xK9_newer-copy==",
        "zZ1undated==",
    ]
    assert "aB3xK9_newer-copy==" in message.content
    assert "aB3xK9_older-copy==" not in message.content


@respx.mock
async def test_numbers_description_lines_and_keeps_posting_details(api_key):
    respx.get(URL).respond(200, text=RESPONSE)

    acme = (await _search(query="backend engineer python")).artifact[1]

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
async def test_leaves_out_jobs_that_break_the_users_preferences(api_key):
    respx.get(URL).respond(200, text=RESPONSE)

    message = await _search(
        Preferences(work_modes=["remote"], countries=["GB"]),
        query="backend engineer python",
    )

    assert [job.id for job in message.artifact] == ["pQ7mN2_newest=="]
    assert "London" not in message.content


@respx.mock
async def test_sends_the_key_and_search_options(api_key):
    route = respx.get(URL).respond(200, text=RESPONSE)

    await _search(query="platform engineer", country="GB", remote_only=True)

    request = route.calls.last.request
    assert request.headers["X-RapidAPI-Key"] == "test-key"
    assert request.headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"
    assert dict(request.url.params) == {
        "query": "platform engineer",
        "country": "gb",
        "work_from_home": "true",
        "date_posted": "week",
    }


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waited: list[float] = []

    async def record(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(jsearch, "sleep", record)
    return waited


@respx.mock
async def test_waits_and_retries_a_rate_limited_search(api_key, waits):
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, json={"message": "Too many requests"}),
            httpx.Response(200, text=RESPONSE),
        ]
    )

    message = await _search(query="backend engineer python")

    assert route.call_count == 2
    assert len(waits) == 1
    assert len(message.artifact) == 3


@respx.mock
async def test_tells_the_agent_when_jsearch_keeps_failing(api_key, waits):
    route = respx.get(URL).respond(503)

    message = await _search(query="backend engineer python")

    assert route.call_count == 3
    assert message.status == "error"
    assert "Job search failed" in message.text


async def test_refuses_to_search_without_a_key(isolate_env):
    reload_settings()

    with pytest.raises(RuntimeError, match="JSEARCH__API_KEY"):
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
