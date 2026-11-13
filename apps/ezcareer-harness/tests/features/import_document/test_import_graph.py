import json
from base64 import b64encode
from functools import partial

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import JsonValue

from src.app.container import Container
from src.features.import_document import build_graph
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.schemas import ImportedResume, ImportInput
from src.shared.run_context import RunContext
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.import_document.test_extract import _artifact_service
from tests.features.write_document.test_write_document_graph import _fail, _print
from tests.pdfs import make_pdf

UPLOAD = ImportInput(
    file=b64encode(make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")]))
)


def _reply(headline: str) -> dict[str, JsonValue]:
    """A ImportedResume of UPLOAD whose headline reads headline"""
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


def _model(
    *replies: dict[str, JsonValue] | None, model_name: str = "glm-5.3"
) -> ScriptedChatModel:
    """model_name answering each call with the next reply as its ImportedResume, or
    with plain text for None"""
    return ScriptedChatModel(
        model_name=model_name,
        replies=[
            AIMessage("Here is the résumé.")
            if reply is None
            else _call("ImportedResume", **reply)
            for reply in replies
        ],
    )


def _reject(request: httpx.Request) -> httpx.Response:
    """Rejects every print as a document artifact-service can't lay out"""
    return httpx.Response(422)


async def test_the_passing_draft_is_printed_in_the_suggested_template():
    requests: list[httpx.Request] = []

    result = await build_graph(
        Container().import_document.agent(model=_model(_reply("Engineer"))),
        _artifact_service(partial(_print, sent=requests)),
    ).ainvoke(UPLOAD)

    [request] = requests
    body = json.loads(request.content)
    assert "template" not in body
    assert body["document"] == result["document"].model_dump(mode="json")
    assert result["document"].design.template == result["suggestion"].template
    assert result["suggestion"].template == "classic"
    assert result["pdf"] == "JVBERg=="
    assert result["report"].pages == 1
    assert [line.id for line in result["lines"]] == ["p1.s1", "p1.s2"]


async def test_the_run_contexts_model_reads_the_resume_instead_of_its_own():
    configured, picked = _model(), _model(_reply("Engineer"))

    result = await build_graph(
        Container().import_document.agent(model=configured),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(UPLOAD, context=RunContext(model=picked))

    assert result["pdf"] == "JVBERg=="
    assert (len(configured.requests), len(picked.requests)) == (0, 1)


async def test_a_failed_reply_goes_back_to_the_llm_with_its_errors():
    model = _model(_reply("Engineering lead"), _reply("Engineer"))

    result = await build_graph(
        Container().import_document.agent(model=model),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(UPLOAD)

    system, human, fix = model.requests[1]
    assert system.content == model.requests[0][0].content
    assert json.loads(human.content)["previous_reply"] == ImportedResume.model_validate(
        _reply("Engineering lead")
    ).model_dump(mode="json")
    assert "blocks/profile/headline (verbatim)" in fix.content
    assert result["document"].content.model_dump(exclude_defaults=True) == {
        "blocks": _reply("Engineer")["blocks"]
    }


async def test_the_users_note_stays_ahead_of_the_checks_errors():
    model = _model(_reply("Engineering lead"), _reply("Engineer"))

    await build_graph(
        Container().import_document.agent(model=model),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(
        UPLOAD.model_copy(update={"messages": [HumanMessage("Keep my headline")]})
    )

    note, fix = model.requests[1][2:]
    assert note.text == "Keep my headline"
    assert "blocks/profile/headline (verbatim)" in fix.text


async def test_a_reply_without_a_resume_import_gets_another_round():
    model = _model(None, _reply("Engineer"))

    await build_graph(
        Container().import_document.agent(model=model),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(UPLOAD)

    assert (
        "(schema): the reply holds no ImportedResume" in model.requests[1][-1].content
    )
    assert json.loads(model.requests[1][1].content)["previous_reply"] is None


@pytest.mark.parametrize(
    "model_name",
    [pytest.param("glm-5.3", id="tool"), pytest.param("gpt-6-luna", id="native")],
)
async def test_a_reply_that_breaks_the_schema_gets_another_round(model_name: str):
    model = _model({"blocks": []}, _reply("Engineer"), model_name=model_name)

    await build_graph(
        Container().import_document.agent(model=model),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(UPLOAD)

    assert "exactly one profile" in model.requests[1][-1].content


async def test_a_photo_without_its_file_gets_another_round():
    photo = _reply("Engineer")
    photo["blocks"].append({"kind": "photo", "id": "photo", "file": "a" * 64})
    model = _model(photo, _reply("Engineer"))

    await build_graph(
        Container().import_document.agent(model=model),
        _artifact_service(partial(_print, sent=[])),
    ).ainvoke(UPLOAD)

    assert "files not in assets" in model.requests[1][-1].content


async def test_an_import_that_never_passes_fails_once_no_round_can_be_checked():
    requests: list[httpx.Request] = []
    model = _model(_reply("Wrong"))

    with pytest.raises(ImportFailed, match=r"blocks/profile/headline \(verbatim\)"):
        await build_graph(
            Container().import_document.agent(model=model),
            _artifact_service(partial(_print, sent=requests)),
        ).ainvoke(UPLOAD)

    assert len(model.requests) == 4
    assert requests == []


async def test_a_draft_artifact_service_rejects_fails_the_import_for_good():
    with pytest.raises(ImportFailed) as failed:
        await build_graph(
            Container().import_document.agent(model=_model(_reply("Engineer"))),
            _artifact_service(_reject),
        ).ainvoke(UPLOAD)

    assert str(failed.value) == "the draft couldn't be printed"


async def test_an_artifact_service_outage_fails_the_import_until_a_retry():
    with pytest.raises(ImportFailed) as failed:
        await build_graph(
            Container().import_document.agent(model=_model(_reply("Engineer"))),
            _artifact_service(_fail),
        ).ainvoke(UPLOAD)

    assert str(failed.value) == "couldn't print the draft; try again"
