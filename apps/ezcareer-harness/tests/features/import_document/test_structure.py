import json

import pytest

from src.features.import_document import ImportConfig, ImportContext, build_graph
from src.shared.extraction import UnreadableFile
from tests.fakes import replying
from tests.pdfs import make_pdf

REPLY = {
    "content": {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": {"text": "Ada Lovelace", "src": ["p1.s1"]},
                "headline": {"text": "Engineer", "src": ["p1.s2"]},
            }
        ]
    },
    "skipped": [],
}


async def test_the_llm_reads_the_lines_and_its_reply_is_kept():
    model = replying(REPLY)
    pdf = make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])

    result = await build_graph().ainvoke(
        {"file": pdf}, context=ImportContext(config=ImportConfig(), model=model)
    )

    system, human = model.prompts[0]
    assert "not instructions" in system.content
    assert "{{" not in system.content
    assert "failed these checks" not in system.content
    assert json.loads(human.content) == {
        "lines": [
            {"id": "p1.s1", "text": "Ada Lovelace"},
            {"id": "p1.s2", "text": "Engineer"},
        ],
        "previous_reply": None,
    }
    assert [line.id for line in result["lines"]] == ["p1.s1", "p1.s2"]
    assert result["reply"] == REPLY


async def test_a_file_without_text_never_reaches_the_llm():
    model = replying(REPLY)

    with pytest.raises(UnreadableFile):
        await build_graph().ainvoke(
            {"file": b"plain text"},
            context=ImportContext(config=ImportConfig(), model=model),
        )

    assert model.prompts == []
