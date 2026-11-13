import json

import pytest
import respx
from langchain_core.messages import AIMessage, ToolMessage

from scripts import probe
from src.app.container import Container
from tests.agents.job_analyst.test_search_jobs import FOUND
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

URL = "https://jobs.example.com/gone"


@respx.mock
async def test_probe_reports_why_an_analysis_failed():
    respx.get(URL).respond(404)

    result = await probe.probe(
        probe.WORKFLOWS["analyse-job"],
        {"url": URL, "facts": [{"id": "py", "text": "Six years of Python"}]},
    )

    assert result["output"] is None
    assert result["error"].startswith("ExecuteError: Couldn't fetch the posting")
    assert result["harness_hash"]


async def test_probe_answers_parallel_searches_each_with_its_own_result(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(probe, "CONTAINER", Container())
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_jobs", "args": {"query": "a"}, "id": "c1"},
                    {"name": "search_jobs", "args": {"query": "b"}, "id": "c2"},
                ],
            ),
            _call("RankedJobs", jobs=[]),
        ]
    )
    probe.CONTAINER.job_analyst.agent(model=model)

    result = await probe.probe(
        probe.WORKFLOWS["find-jobs"],
        {
            "facts": [{"id": "py", "text": "Six years of Python"}],
            "tool_results": {"job_search": [FOUND, {**FOUND, "requests_left": 1}]},
        },
    )

    assert (result["error"], result["output"]) == (None, {"jobs": []})
    searched = [m for m in model.requests[-1] if isinstance(m, ToolMessage)][-2:]
    assert sorted(json.loads(m.text)["requests_left"] for m in searched) == [
        1,
        FOUND["requests_left"],
    ]
