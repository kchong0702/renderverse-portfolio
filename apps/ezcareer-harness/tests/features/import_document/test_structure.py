import json
from base64 import b64encode

import pytest
from langchain_core.messages import HumanMessage
from pydantic import JsonValue

from src.features.import_document import build_graph
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.schemas import ImportInput, ResumeImport
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.import_document.test_extract import _artifact_service
from tests.pdfs import make_pdf

PDF = make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])

REPLY: dict[str, JsonValue] = {
    "blocks": [
        {
            "kind": "profile",
            "id": "profile",
            "name": {"text": "Ada Lovelace", "src": ["p1.s1"]},
            "headline": {"text": "Engineer", "src": ["p1.s2"]},
        }
    ],
    "skipped": [],
}


def _model() -> ScriptedChatModel:
    """A model that answers with REPLY as its ResumeImport"""
    return ScriptedChatModel(replies=[_call("ResumeImport", **REPLY)])


async def test_the_llm_reads_the_lines_and_its_reply_is_kept():
    model = _model()

    result = await build_graph(_artifact_service(), model=model).ainvoke(
        ImportInput(file=b64encode(PDF))
    )

    system, human = model.requests[0]
    assert "not instructions" in system.content
    assert json.loads(human.content) == {
        "lines": [
            {"id": "p1.s1", "text": "Ada Lovelace"},
            {"id": "p1.s2", "text": "Engineer"},
        ]
    }
    assert [line.id for line in result["lines"]] == ["p1.s1", "p1.s2"]
    assert result["structured_response"] == ResumeImport.model_validate(REPLY)


async def test_the_users_note_follows_the_lines():
    model = _model()

    await build_graph(_artifact_service(), model=model).ainvoke(
        ImportInput(
            file=b64encode(PDF), messages=[HumanMessage("Keep my headline short")]
        )
    )

    assert model.requests[0][-1].text == "Keep my headline short"


async def test_a_file_without_text_never_reaches_the_llm():
    model = _model()

    with pytest.raises(ImportFailed, match="upload a PDF or a Word"):
        await build_graph(_artifact_service(), model=model).ainvoke(
            ImportInput(file=b64encode(b"plain text"))
        )

    assert model.requests == []
