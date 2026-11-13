import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from structlog.testing import capture_logs

from src.features.connections import Connection
from src.features.jobs.tools.job_search import JobSearchRequest
from tests.conftest import (
    PREFIX,
    a2a_sent,
    a2a_task,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
    work,
)

JOBS = f"{PREFIX}/jobs"
JSEARCH = f"{PREFIX}/settings/connections/jsearch"
API_KEY = "rapidapi-key-0123456789"
FIXTURES = Path(__file__).parent / "fixtures"
SEARCH = {
    "execute_tool": "job_search",
    "query": "backend engineer",
    "location": None,
    "country": "GB",
    "remote_only": False,
    "posted_within": "week",
    "employment_types": [],
    "job_requirements": [],
    "radius_km": None,
    "max_jobs": 10,
}
ACME = {
    "id": "js-1",
    "title": "Backend Engineer",
    "company": "Acme",
    "location": "",
    "country": None,
    "remote": False,
    "posted_at": None,
    "apply_url": "https://jobs.example.com/1",
    "lines": [],
}


def _searching(request: dict = SEARCH) -> dict:
    """find-jobs pausing to ask ops-api for a job search"""
    return a2a_task("INPUT_REQUIRED", status_parts=[{"data": request}])


def _ending(sent: dict) -> dict:
    """find-jobs ending on ops-api's answer: failing with an error's reason, else
    finding nothing"""
    [part] = sent["params"]["message"]["parts"]
    if "error" in part["data"]:
        return a2a_task("FAILED", status_parts=[{"text": part["data"]["error"]}])
    return a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}])


async def _find(app, client, harness, request: dict = SEARCH) -> dict:
    """Run Find through the worker, find-jobs searching once; the run as it ends"""
    harness.outcomes = [_searching(request), _ending]
    assert (await client.post(f"{JOBS}/find")).status_code == 202
    await work(app)
    return (await client.get(f"{JOBS}/runs/latest")).json()


def _answer(harness) -> dict:
    """What ops-api last answered the harness"""
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]


async def _ask_assistant(client, harness) -> list[dict]:
    """Ask the assistant for jobs, find-jobs searching once inside its run"""
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": SEARCH}])],
        [
            stream_chunk("a-1", "career-director", {"text": "None fit yet."}),
            stream_status("COMPLETED"),
        ],
    ]
    response = await client.post(
        f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f/messages",
        json={"text": "Find me backend jobs"},
    )
    return sse_events(response)


async def test_find_searches_jsearch_on_the_users_key_and_answers_its_postings(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    run = await _find(app, client, harness)

    assert (run["status"], run["error"]) == ("done", "")
    [request] = jsearch.received
    assert request.headers["X-RapidAPI-Key"] == API_KEY
    assert dict(request.url.params) == {
        "query": "backend engineer",
        "country": "gb",
        "work_from_home": "false",
        "date_posted": "week",
    }
    assert _answer(harness) == {"jobs": [ACME], "requests_left": 180}


async def test_each_search_option_becomes_its_jsearch_parameter(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    await _find(
        app,
        client,
        harness,
        SEARCH
        | {
            "location": "London",
            "remote_only": True,
            "posted_within": "day",
            "employment_types": ["full_time", "part_time", "contract", "internship"],
            "job_requirements": ["no_degree"],
            "radius_km": 25,
        },
    )

    assert dict(jsearch.received[0].url.params) == {
        "query": "backend engineer in London",
        "country": "gb",
        "work_from_home": "true",
        "date_posted": "today",
        "employment_types": "FULLTIME,PARTTIME,CONTRACTOR,INTERN",
        "job_requirements": "no_degree",
        "radius": "25",
    }


@pytest.mark.parametrize(
    ("posted_within", "date_posted"),
    [(None, "all"), ("day", "today"), ("week", "week"), ("month", "month")],
)
async def test_how_recent_the_jobs_must_be_becomes_jsearchs_date_posted(
    app, client, harness, jsearch, posted_within, date_posted
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    await _find(app, client, harness, SEARCH | {"posted_within": posted_within})

    assert jsearch.received[0].url.params["date_posted"] == date_posted


def test_reads_the_request_the_harness_sends_exactly_as_the_harness_serialises_it():
    request = json.loads((FIXTURES / "job_search_request.json").read_text())

    assert JobSearchRequest.model_validate(request).model_dump(mode="json") == request


async def test_answers_jsearchs_jobs_newest_first_each_once_as_the_harness_reads_them(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    jsearch.jobs = json.loads((FIXTURES / "jsearch_search.json").read_text())["data"][
        "jobs"
    ]

    await _find(app, client, harness)

    assert _answer(harness) == json.loads(
        (FIXTURES / "job_search_answer.json").read_text()
    )


@pytest.mark.parametrize(
    ("preferences", "kept"),
    [
        ({"countries": ["US"]}, []),
        ({"work_modes": ["remote"]}, ["pQ7mN2_newest=="]),
        (
            {"work_modes": ["onsite", "hybrid"], "countries": ["GB"]},
            ["aB3xK9_newer-copy==", "zZ1undated=="],
        ),
    ],
)
async def test_leaves_out_jobs_that_break_the_users_work_mode_or_country(
    app, client, harness, jsearch, preferences, kept
):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    await client.patch(f"{PREFIX}/preferences", json=preferences)
    jsearch.jobs = json.loads((FIXTURES / "jsearch_search.json").read_text())["data"][
        "jobs"
    ]

    await _find(app, client, harness)

    assert [job["id"] for job in _answer(harness)["jobs"]] == kept


async def test_the_assistant_answers_a_search_find_jobs_makes_in_its_run(
    client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    events = await _ask_assistant(client, harness)

    assert events[-1] == {"status": "completed", "reply": "None fit yet."}
    assert jsearch.received[0].headers["X-RapidAPI-Key"] == API_KEY
    assert _answer(harness) == {"jobs": [ACME], "requests_left": 180}


async def test_the_key_never_reaches_the_harness_or_the_logs(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    with capture_logs() as logs:
        await _find(app, client, harness)
        await _ask_assistant(client, harness)
        jsearch.status = 401
        refused = await _find(app, client, harness)

    assert len(jsearch.received) == 3
    assert {request.headers["X-RapidAPI-Key"] for request in jsearch.received} == {
        API_KEY
    }
    assert refused["error"] == "JSearch answered 401"
    assert len(harness.received) == 6
    assert [
        request.url.path
        for request in harness.received
        if API_KEY in f"{request.headers} {request.content.decode()}"
    ] == []
    assert API_KEY not in str(logs) + refused["error"]


async def test_settings_shows_the_quota_jsearch_last_reported(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    await _find(app, client, harness)
    jsearch.headers = {
        "x-ratelimit-requests-remaining": "179",
        "x-ratelimit-requests-limit": "200",
    }

    await _find(app, client, harness)

    [connection] = [
        c
        for c in (await client.get(f"{PREFIX}/settings")).json()["connections"]
        if c["id"] == "jsearch"
    ]
    assert connection["quota"] == {"remaining": 179, "limit": 200}
    assert _answer(harness)["requests_left"] == 179


async def test_without_a_key_find_fails_at_once_with_the_settings_message(
    app, client, harness, jsearch
):
    run = await _find(app, client, harness)

    assert (run["status"], run["error"]) == (
        "failed",
        "Connect JSearch in Settings to search for jobs",
    )
    assert jsearch.received == []
    assert len(harness.received) == 2


async def test_an_unreadable_key_fails_find_with_a_way_to_fix_it(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    async with app.state.session_factory() as session, session.begin():
        stored = await session.scalar(select(Connection))
        stored.secret = Fernet(Fernet.generate_key()).encrypt(b"other")

    run = await _find(app, client, harness)

    assert (run["status"], run["error"]) == (
        "failed",
        "Ops can no longer read your JSearch key; change it in Settings",
    )
    assert jsearch.received == []


async def test_a_search_with_any_field_beyond_the_neutral_search_is_refused(
    app, client, harness, jsearch
):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    run = await _find(
        app, client, harness, SEARCH | {"url": "https://attacker.example/"}
    )

    assert run["status"] == "failed"
    assert "Extra inputs are not permitted" in run["error"]
    assert jsearch.received == []
