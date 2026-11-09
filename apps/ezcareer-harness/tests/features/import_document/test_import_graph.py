import json
from base64 import b64encode

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from pydantic import JsonValue

from src.features.import_document import build_graph
from src.features.import_document.schemas import ImportInput, ResumeImport
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.import_document.test_extract import _artifact_service
from tests.pdfs import make_pdf

UPLOAD = ImportInput(
    file=b64encode(make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")]))
)


def _reply(headline: str) -> dict[str, JsonValue]:
    """A ResumeImport of UPLOAD whose headline reads headline"""
    return {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": {"text": "Ada Lovelace", "src": ["p1.s1"]},
                "headline": {"text": headline, "src": ["p1.s2"]},
            }
        ]
    }


def _model(*replies: dict[str, JsonValue] | None) -> ScriptedChatModel:
    """A model that answers each call with the next reply as its ResumeImport, or
    with plain text for None"""
    return ScriptedChatModel(
        replies=[
            AIMessage("Here is the résumé.")
            if reply is None
            else _call("ResumeImport", **reply)
            for reply in replies
        ]
    )


async def test_a_failed_reply_goes_back_to_the_llm_with_its_errors():
    model = _model(_reply("Engineering lead"), _reply("Engineer"))

    result = await build_graph(_artifact_service(), model=model).ainvoke(UPLOAD)

    system, human, fix = model.requests[1]
    assert system.content == model.requests[0][0].content
    assert json.loads(human.content)["previous_reply"] == ResumeImport.model_validate(
        _reply("Engineering lead")
    ).model_dump(mode="json")
    assert "blocks/profile/headline (verbatim)" in fix.content
    assert "blocks (coverage)" in fix.content
    assert result["errors"] == []
    assert result["structured_response"] == ResumeImport.model_validate(
        _reply("Engineer")
    )


async def test_the_users_note_stays_ahead_of_the_checks_errors():
    model = _model(_reply("Engineering lead"), _reply("Engineer"))

    await build_graph(_artifact_service(), model=model).ainvoke(
        UPLOAD.model_copy(update={"messages": [HumanMessage("Keep my headline")]})
    )

    note, fix = model.requests[1][2:]
    assert note.text == "Keep my headline"
    assert "blocks/profile/headline (verbatim)" in fix.text


async def test_a_reply_without_a_resume_import_gets_another_round():
    model = _model(None, _reply("Engineer"))

    result = await build_graph(_artifact_service(), model=model).ainvoke(UPLOAD)

    assert "(schema): the reply holds no ResumeImport" in model.requests[1][-1].content
    assert json.loads(model.requests[1][1].content)["previous_reply"] is None
    assert result["errors"] == []


async def test_a_reply_that_breaks_the_schema_gets_another_round():
    model = _model({"blocks": []}, _reply("Engineer"))

    result = await build_graph(_artifact_service(), model=model).ainvoke(UPLOAD)

    assert "exactly one profile" in model.requests[1][-1].content
    assert result["errors"] == []


async def test_an_import_that_never_passes_stops_at_the_recursion_limit():
    model = _model(_reply("Wrong"))

    with pytest.raises(GraphRecursionError):
        await build_graph(_artifact_service(), model=model).ainvoke(UPLOAD)

    assert len(model.requests) == 4
