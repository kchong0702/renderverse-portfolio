from pathlib import Path

import pytest
import respx

from src.core.config import reload_settings
from src.features.find_jobs.tools import search_jobs

URL = "https://jsearch.p.rapidapi.com/search"
RESPONSE = (Path(__file__).parent / "fixtures" / "jsearch_search.json").read_text()


@pytest.fixture
def api_key(isolate_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EZCAREER_HARNESS_JSEARCH__API_KEY", "test-key")
    reload_settings()
    yield
    monkeypatch.undo()
    reload_settings()


async def _search(**args):
    message = await search_jobs.ainvoke(
        {"type": "tool_call", "id": "1", "name": "search_jobs", "args": args}
    )
    return message


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

    assert (acme.title, acme.company, acme.location, acme.remote) == (
        "Senior Backend Engineer",
        "ACME",
        "London, GB",
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


async def test_refuses_to_search_without_a_key(isolate_env):
    reload_settings()

    with pytest.raises(RuntimeError, match="JSEARCH__API_KEY"):
        await _search(query="anything")
