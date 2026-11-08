from pathlib import Path

import pytest
import respx
from langchain_core.messages import AIMessage, HumanMessage

from src.app.container import Container
from src.core.config import reload_settings
from src.features.find_jobs import build_graph
from tests.conftest import ScriptedChatModel

RESPONSE = (Path(__file__).parent / "fixtures" / "jsearch_search.json").read_text()
INPUT = {
    "profile": {
        "facts": [{"id": "py", "text": "Six years of Python in production"}],
        "preferences": {"countries": ["GB"]},
    }
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


@pytest.fixture
def jsearch(isolate_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EZCAREER_HARNESS_JSEARCH__API_KEY", "test-key")
    reload_settings()
    with respx.mock:
        respx.get("https://jsearch.p.rapidapi.com/search-v2").respond(
            200, text=RESPONSE
        )
        yield
    monkeypatch.undo()
    reload_settings()


async def test_unknown_jobs_go_back_and_the_ranking_comes_out_by_fit(jsearch):
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
    result = await build_graph(
        container.job_finder(model=model), container.job_sources()
    ).ainvoke(INPUT)

    assert [(job.posting.id, job.fit) for job in result["jobs"]] == [
        ("aB3xK9_newer-copy==", 100),
        ("pQ7mN2_newest==", 0),
    ]
    assert result["jobs"][0].posting.apply_url == (
        "https://careers.acme.example/jobs/42"
    )
    feedback = [m.text for m in model.requests[-1] if isinstance(m, HumanMessage)]
    assert '"GB"' in feedback[0]
    assert "unknown_job" in feedback[-1]
