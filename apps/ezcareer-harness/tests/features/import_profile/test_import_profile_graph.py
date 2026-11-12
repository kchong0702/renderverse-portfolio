import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import JsonValue

from src.app.container import Container
from src.core.errors import ExecuteError
from src.features.import_profile import ImportProfileInput, build_graph
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

EXPORT = ImportProfileInput.model_validate(
    {
        "files": [
            {
                "name": "Profile.csv",
                "rows": [
                    {
                        "First Name": "Ada",
                        "Headline": "Backend engineer",
                        "Summary": "I build payment systems.",
                        "Geo Location": "Kuala Lumpur",
                        "Websites": "[PORTFOLIO:https://ada.dev]",
                    }
                ],
            },
            {
                "name": "Positions.csv",
                "rows": [
                    {
                        "Company Name": "Acme",
                        "Title": "Senior Engineer",
                        "Description": "Led the payments team.\n- Cut checkout"
                        " latency by 40%.\n- Moved billing to Go.",
                        "Started On": "Jan 2021",
                        "Finished On": "",
                    },
                    {
                        "Company Name": "Initech",
                        "Title": "Engineer",
                        "Description": "Rewrote billing in Go.",
                        "Started On": "Mar 2018",
                        "Finished On": "Dec 2020",
                    },
                ],
            },
            {"name": "Skills.csv", "rows": [{"Name": "Go"}]},
        ]
    }
)


def _reply(highlight: str, start: str = "2021-01") -> dict[str, JsonValue]:
    """A ProfileImport of EXPORT's Acme role whose second highlight reads highlight,
    starting at start"""
    return {
        "about": {
            "headline": "Backend engineer",
            "summary": "I build payment systems.",
            "location": "Kuala Lumpur",
            "links": [{"label": "Portfolio", "url": "https://ada.dev"}],
        },
        "entries": [
            {
                "kind": "role",
                "title": "Senior Engineer",
                "organisation": "Acme",
                "start": start,
                "end": "present",
                "summary": "Led the payments team.",
                "highlights": ["Cut checkout latency by 40%", highlight],
            }
        ],
        "skills": [{"name": "Go", "group": "Languages"}],
    }


def _model(*replies: dict[str, JsonValue] | None) -> ScriptedChatModel:
    """A model answering each call with the next reply as its ProfileImport, or
    with plain text for None"""
    return ScriptedChatModel(
        replies=[
            AIMessage("Here is the profile.")
            if reply is None
            else _call("ProfileImport", **reply)
            for reply in replies
        ]
    )


def _graph(model: ScriptedChatModel):
    return build_graph(Container().import_document.agent(model=model))


async def test_a_passing_import_comes_back_as_about_entries_and_skills():
    model = _model(_reply("Moved billing to Go."))

    result = await _graph(model).ainvoke(EXPORT)

    assert {
        key: [item.model_dump(mode="json", exclude_defaults=True) for item in value]
        if isinstance(value, list)
        else value.model_dump(mode="json", exclude_defaults=True)
        for key, value in result.items()
    } == _reply("Moved billing to Go.")
    files = json.loads(model.requests[0][1].content)["files"]
    assert [file["name"] for file in files] == [
        "Profile.csv",
        "Positions.csv",
        "Skills.csv",
    ]


async def test_an_invented_highlight_goes_back_with_the_previous_reply():
    model = _model(_reply("Moved all billing to Go"), _reply("Moved billing to Go"))

    result = await _graph(model).ainvoke(EXPORT)

    _, human, fix = model.requests[1]
    previous = json.loads(human.content)["previous_reply"]
    assert previous["entries"][0]["highlights"][1] == "Moved all billing to Go"
    assert "entries/0/highlights/1 (verbatim)" in fix.content
    assert result["entries"][0].highlights[1] == "Moved billing to Go"


async def test_a_highlight_from_another_rows_description_goes_back():
    model = _model(_reply("Rewrote billing in Go"), _reply("Moved billing to Go"))

    await _graph(model).ainvoke(EXPORT)

    assert (
        "entries/0/highlights/1 (verbatim): 'Rewrote billing in Go' is not word for"
        " word in the row of 'Senior Engineer'" in model.requests[1][-1].content
    )


async def test_a_year_the_row_doesnt_state_goes_back():
    model = _model(
        _reply("Moved billing to Go", start="2020-01"), _reply("Moved billing to Go")
    )

    await _graph(model).ainvoke(EXPORT)

    assert "entries/0/start (verbatim): '2020'" in model.requests[1][-1].content


async def test_a_reply_without_a_profile_import_gets_another_round():
    model = _model(None, _reply("Moved billing to Go"))

    await _graph(model).ainvoke(EXPORT)

    assert "(schema): the reply holds no ProfileImport" in model.requests[1][-1].content


async def test_the_users_note_stays_ahead_of_the_checks_errors():
    model = _model(_reply("Moved all billing to Go"), _reply("Moved billing to Go"))

    await _graph(model).ainvoke(
        EXPORT.model_copy(update={"messages": [HumanMessage("Skip my skills")]})
    )

    note, fix = model.requests[1][2:]
    assert note.text == "Skip my skills"
    assert "(verbatim)" in fix.text


async def test_an_import_that_never_passes_fails_once_no_round_can_be_checked():
    model = _model(_reply("Moved all billing to Go"))

    with pytest.raises(ExecuteError, match=r"entries/0/highlights/1 \(verbatim\)"):
        await _graph(model).ainvoke(EXPORT)

    assert len(model.requests) == 5
