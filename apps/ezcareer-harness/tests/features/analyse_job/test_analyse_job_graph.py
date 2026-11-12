import json
from pathlib import Path

import pytest
import respx
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from src.agents import load_agents
from src.app.container import Container
from src.core.config import get_settings, reload_settings
from src.core.errors import ExecuteError
from src.features.analyse_job import build_graph
from src.infrastructure.observability import tracing
from src.infrastructure.observability.instrumentation import instrument
from tests.conftest import ScriptedChatModel

URL = "https://jobs.example.com/acme/senior-backend"
POSTING = (Path(__file__).parent / "fixtures" / "posting.html").read_text()
INPUT = {
    "url": URL,
    "facts": [
        {
            "id": "acme",
            "text": "Backend engineer at Initech, Python and Django",
            "start": "2018-01",
            "end": "present",
        },
    ],
    "preferences": {"work_modes": ["remote"]},
}


def _call(name: str, **args) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}]
    )


def _answer(python_text: str) -> AIMessage:
    return _call(
        "JobRequirements",
        requirements=[
            {
                "text": python_text,
                "importance": "required",
                "line_ids": [6],
                "match": "met",
                "fact_ids": ["fact:acme"],
                "reason": "Python at Initech since 2018.",
            },
            {
                "text": "Kubernetes",
                "importance": "nice_to_have",
                "line_ids": [10],
                "match": "not_met",
                "fact_ids": [],
                "reason": "No fact mentions Kubernetes.",
            },
        ],
        terms={"min_years": {"value": 5, "line_ids": [6]}},
    )


def _scripted(*answers: AIMessage) -> ScriptedChatModel:
    return ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/analyse-job/SKILL.md"),
            _call("read_profile_facts"),
            *answers,
        ]
    )


@pytest.fixture
def posting():
    with respx.mock:
        respx.get(URL).respond(200, html=POSTING)
        yield


async def test_check_errors_go_back_and_the_fixed_answer_is_scored(posting):
    model = _scripted(
        _answer("Five years of Python"), _answer("5+ years of Python in production")
    )

    result = await build_graph(Container().job_analyst.agent(model=model)).ainvoke(
        INPUT
    )

    analysis = result["analysis"]
    assert analysis.fit == 67
    assert [(f.kind.value, f.passed) for f in analysis.filters] == [("years", True)]
    feedback = [m.text for m in model.requests[-1] if isinstance(m, HumanMessage)]
    assert "not_verbatim" in feedback[-1]
    facts = next(
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "read_profile_facts"
    )
    assert facts.startswith("fact:acme  (2018-01 to present) Backend engineer")


async def test_posting_reaches_the_agent_as_untrusted_numbered_lines(posting):
    model = _scripted(_answer("5+ years of Python in production"))

    await build_graph(Container().job_analyst.agent(model=model)).ainvoke(INPUT)

    prompt = model.requests[0][1].text
    assert "<posting untrusted>" in prompt
    assert "[6] 5+ years of Python in production" in prompt


async def test_an_agent_that_never_cites_correctly_hits_the_recursion_limit(
    posting,
):
    model = _scripted(_answer("Five years of Python"))

    with pytest.raises(GraphRecursionError):
        await build_graph(Container().job_analyst.agent(model=model)).ainvoke(INPUT)


async def test_a_missing_posting_fails_the_flow():
    with respx.mock:
        respx.get(URL).respond(404)
        with pytest.raises(ExecuteError, match="Couldn't fetch the posting"):
            await build_graph(Container().job_analyst.agent(model=_scripted())).ainvoke(
                INPUT
            )


async def test_trace_records_the_agent_hash_check_rounds_and_tool_calls(
    posting, make_settings, span_exporters
):
    instrument(
        make_settings(
            tracing_enabled=True,
            otlp_endpoint="http://collector:4318",
            instrumentations=["langchain"],
        )
    )
    model = _scripted(
        _answer("Five years of Python"), _answer("5+ years of Python in production")
    )

    await build_graph(Container().job_analyst.agent(model=model)).ainvoke(INPUT)
    tracing.shutdown_tracing()

    [exporter] = span_exporters
    checks = [s for s in exporter.spans if s.name == "check"]
    assert [s.attributes["check.error_count"] for s in checks] == [1, 0]
    assert json.loads(checks[0].attributes["check.errors"])[0]["rule"] == (
        "not_verbatim"
    )
    assert {s.context.trace_id for s in exporter.spans} == {checks[0].context.trace_id}
    assert load_agents(get_settings().agents)["job-analyst"].hash in {
        json.loads(s.attributes["metadata"]).get("agent_hash")
        for s in exporter.spans
        if "metadata" in s.attributes
    }
    assert "read_profile_facts" in {s.name for s in exporter.spans}


async def test_candidate_configurations_without_the_check_take_the_first_answer(
    posting, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    settings = get_settings()
    configurations = tmp_path / "configurations.yaml"
    configurations.write_text(
        settings.graph_profile("analyse-job")
        .path.read_text()
        .replace("[citations]", "[]")
    )
    [agent] = [a for a in settings.agents if a.name == "job-analyst"]
    config = tmp_path / "config.toml"
    config.write_text(
        f'[models]\n{agent.family} = ["{agent.model}"]\n\n'
        f'[[agents]]\nname = "job-analyst"\npath = "{agent.path}"\n'
        f'family = "{agent.family}"\nmodel = "{agent.model}"\n\n'
        f'[[graph_profiles]]\nname = "analyse-job"\npath = "{configurations}"\n'
    )
    monkeypatch.setenv("EZCAREER_HARNESS_CONFIG", str(config))
    reload_settings()
    model = _scripted(
        _answer("Five years of Python"), _answer("5+ years of Python in production")
    )

    result = await build_graph(Container().job_analyst.agent(model=model)).ainvoke(
        INPUT
    )
    monkeypatch.undo()
    reload_settings()

    assert result["analysis"].requirements[0].text == "Five years of Python"
    assert len(model.requests) == 3


async def test_an_agent_that_ends_without_an_answer_is_asked_for_one(posting):
    model = _scripted(
        AIMessage("It looks like a good fit."),
        _answer("5+ years of Python in production"),
    )

    result = await build_graph(Container().job_analyst.agent(model=model)).ainvoke(
        INPUT
    )

    assert result["analysis"].fit == 67
    feedback = [m.text for m in model.requests[-1] if isinstance(m, HumanMessage)]
    assert "no_answer" in feedback[-1]


async def test_the_graph_gets_the_same_analysis_from_native_output_and_an_answer_tool(
    posting,
):
    answer = _answer("5+ years of Python in production")
    by_tool = _scripted(answer)
    native = _scripted(answer).model_copy(update={"model_name": "gpt-6-luna"})

    from_tool = await build_graph(Container().job_analyst.agent(model=by_tool)).ainvoke(
        INPUT
    )
    from_native = await build_graph(
        Container().job_analyst.agent(model=native)
    ).ainvoke(INPUT)

    assert "JobRequirements" in by_tool.offered_tools[-1]
    assert "JobRequirements" not in native.offered_tools[-1]
    assert from_tool["analysis"] == from_native["analysis"]
    assert from_native["analysis"].fit == 67
