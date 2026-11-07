import json

import pytest
from langchain_core.tracers.context import collect_runs

from src.features.import_document import ImportConfig, ImportFailed, run_import
from src.shared.checks.resume import Check
from tests.fakes import replying
from tests.pdfs import make_pdf

PDF = make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])


def answer(headline: str) -> dict:
    return {
        "content": {
            "blocks": [
                {
                    "kind": "profile",
                    "id": "profile",
                    "name": {"text": "Ada Lovelace", "src": ["p1.s1"]},
                    "headline": {"text": headline, "src": ["p1.s2"]},
                }
            ]
        }
    }


async def test_a_failed_reply_goes_back_to_the_llm_with_its_errors():
    model = replying(answer("Engineering lead"), answer("Engineer"))

    result = await run_import(PDF, ImportConfig(), model)

    assert [[e.rule for e in errors] for errors in result["rounds"]] == [
        [Check.VERBATIM],
        [],
    ]
    system, human = model.prompts[1]
    assert "failed these checks" in system.content
    assert "verbatim at content/blocks/profile/headline" in system.content
    assert json.loads(human.content)["previous_reply"] == answer("Engineering lead")
    assert result["reply"] == answer("Engineer")


async def test_an_import_that_never_passes_fails_at_the_recursion_limit():
    model = replying(*[answer("Wrong")] * 10)

    with pytest.raises(ImportFailed, match="couldn't read this file"):
        await run_import(PDF, ImportConfig(recursion_limit=5), model)

    assert len(model.prompts) == 2


async def test_a_file_without_text_fails_the_import():
    with pytest.raises(ImportFailed):
        await run_import(b"%PDF-1.7 broken", ImportConfig(), replying())


async def test_each_run_records_its_config_version():
    config = ImportConfig(prompt="Read the résumé.")

    with collect_runs() as runs:
        await run_import(PDF, config, replying(answer("Engineer")))

    assert runs.traced_runs[0].extra["metadata"]["import_config"] == config.version
    assert ImportConfig(prompt="Read the résumé carefully.").version != config.version
