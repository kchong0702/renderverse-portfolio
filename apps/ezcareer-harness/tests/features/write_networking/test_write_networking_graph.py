import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from pydantic import JsonValue, ValidationError

from src.app.container import Container
from src.core.errors import ExecuteError
from src.features.write_networking import WriteNetworkingInput, build_graph
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

REQUEST: dict[str, JsonValue] = {
    "aim": "Staff backend engineer",
    "facts": [
        {
            "id": "role-acme",
            "text": "Senior Engineer at Acme, Kuala Lumpur\nLed the payments team.\n"
            "Cut checkout latency by 40%.",
            "start": "2021-01",
            "end": "present",
        },
        {
            "id": "project-ledger",
            "text": "Project Ledger\nAn open-source double-entry ledger in Go.",
        },
        {"id": "education-um", "text": "BSc Computer Science, Universiti Malaya"},
        {"id": "skill-go", "text": "Languages: Go"},
    ],
}

ROLE = {
    "fact": "role-acme",
    "text": "Led the payments team at Acme.\n• Cut checkout latency by 40%.",
    "facts": ["role-acme"],
}
PROJECT = {
    "fact": "project-ledger",
    "text": "• An open-source double-entry ledger in Go.",
    "facts": ["project-ledger"],
}


def _answer(
    headline: str = "Backend engineer for payments | Go",
    descriptions: list[JsonValue] | None = None,
) -> AIMessage:
    return _call(
        "NetworkingCopy",
        headline={"text": headline, "facts": ["role-acme", "skill-go"]},
        summary={
            "text": "I lead payments engineering at Acme.",
            "facts": ["role-acme"],
        },
        descriptions=[ROLE, PROJECT] if descriptions is None else descriptions,
    )


def _scripted(*answers: AIMessage) -> ScriptedChatModel:
    return ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/write-networking-copy/SKILL.md"),
            _call("read_profile_facts"),
            *answers,
        ]
    )


def _graph(model: ScriptedChatModel):
    return build_graph(Container().career_consultant.agent(model=model))


def _fix(model: ScriptedChatModel) -> str:
    return [m.text for m in model.requests[-1] if isinstance(m, HumanMessage)][-1]


async def test_the_copy_comes_back_with_its_citations():
    model = _scripted(_answer())

    result = await _graph(model).ainvoke(REQUEST)

    assert result["headline"].model_dump() == {
        "text": "Backend engineer for payments | Go",
        "facts": ["role-acme", "skill-go"],
    }
    assert result["summary"].text == "I lead payments engineering at Acme."
    assert [d.model_dump() for d in result["descriptions"]] == [ROLE, PROJECT]
    brief = model.requests[0][1].text
    assert "aimed at jobs like: Staff backend engineer" in brief
    assert "a description of fact:role-acme, a description of fact:project-ledger." in (
        brief
    )
    assert "the headline at most 220 characters" in brief
    facts = next(
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "read_profile_facts"
    )
    assert "fact:skill-go  Languages: Go" in facts


async def test_missing_entries_unknown_facts_caps_and_markdown_go_back():
    model = _scripted(
        _answer(
            headline="Backend engineer " + "x" * 210,
            descriptions=[
                {**ROLE, "text": "Led it.\n- Led the **payments** team."},
                {**PROJECT, "facts": ["project-zeta"]},
                {**PROJECT, "fact": "education-um"},
            ],
        ),
        _answer(),
    )

    await _graph(model).ainvoke(REQUEST)

    fix = _fix(model)
    assert "headline (too_long): is 227 characters; cut it to 220" in fix
    assert "role-acme (not_plain): '-' is Markdown or HTML" in fix
    assert "project-ledger (unknown_fact): project-zeta are not facts" in fix
    assert "education-um (unknown_fact): education-um is not a role or project" in fix


async def test_a_left_out_description_goes_back_and_the_fix_is_kept():
    model = _scripted(_answer(descriptions=[ROLE]), _answer())

    result = await _graph(model).ainvoke(REQUEST)

    assert "project-ledger (missing): describe project-ledger" in _fix(model)
    assert [d.fact for d in result["descriptions"]] == ["role-acme", "project-ledger"]


async def test_only_returns_just_the_field_asked_for():
    model = _scripted(_answer(descriptions=[PROJECT]))

    result = await _graph(model).ainvoke({**REQUEST, "only": "project-ledger"})

    assert result["headline"] is None
    assert result["summary"] is None
    assert [d.fact for d in result["descriptions"]] == ["project-ledger"]
    assert "Write only a description of fact:project-ledger." in (
        model.requests[0][1].text
    )


async def test_an_agent_that_never_fixes_its_copy_hits_the_recursion_limit():
    model = _scripted(_answer(headline="**Backend engineer** | Go"))

    with pytest.raises(GraphRecursionError):
        await _graph(model).ainvoke(REQUEST)


async def test_a_profile_without_facts_fails_the_flow():
    with pytest.raises(ExecuteError, match="No profile facts"):
        await _graph(_scripted()).ainvoke({"facts": []})


@pytest.mark.parametrize("only", ["skill-go", "education-um", "role-zeta"])
def test_only_names_the_headline_summary_or_a_role_or_project(only: str):
    with pytest.raises(ValidationError, match="is not headline, summary or a role"):
        WriteNetworkingInput.model_validate({**REQUEST, "only": only})
