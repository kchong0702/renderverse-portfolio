import json

import httpx
import pytest
from langchain_core.tracers.context import collect_runs

from src.features.import_document import ImportConfig, ImportFailed, run_import
from src.shared.checks.resume import Check
from tests.fakes import artifact_service, replying
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


async def test_a_failed_reply_goes_back_to_the_llm_with_its_errors(
    config: ImportConfig,
):
    model = replying(answer("Engineering lead"), answer("Engineer"))

    result = await run_import(PDF, config, artifact_service([]), model)

    assert [[e.rule for e in errors] for errors in result.rounds] == [
        [Check.VERBATIM],
        [],
    ]
    system, human = model.prompts[1]
    assert "failed these checks" in system.content
    assert "verbatim at content/blocks/profile/headline" in system.content
    assert json.loads(human.content)["previous_reply"] == answer("Engineering lead")
    assert (
        result.document.content.model_dump(exclude_defaults=True)
        == answer("Engineer")["content"]
    )


async def test_the_passing_draft_is_printed_in_the_default_template(
    config: ImportConfig,
):
    requests: list[httpx.Request] = []

    result = await run_import(
        PDF, config, artifact_service(requests), replying(answer("Engineer"))
    )

    [request] = requests
    body = json.loads(request.content)
    assert body["template"] == {"id": "classic", "kinds": ["resume", "cv"]}
    assert body["document"] == result.document.model_dump(mode="json")
    assert result.document.design.template == "classic"
    assert result.document.design.layouts == {}
    assert result.pdf == b"%PDF-fake"
    assert result.report.pages == 1
    assert [line.id for line in result.lines] == ["p1.s1", "p1.s2"]
    assert result.config_version == config.version


async def test_an_import_that_never_passes_fails_at_the_recursion_limit(
    config: ImportConfig,
):
    model = replying(*[answer("Wrong")] * 10)
    requests: list[httpx.Request] = []

    with pytest.raises(ImportFailed, match="couldn't read this file"):
        await run_import(
            PDF,
            config.model_copy(update={"recursion_limit": 5}),
            artifact_service(requests),
            model,
        )

    assert requests == []

    assert len(model.prompts) == 2


async def test_a_file_without_text_fails_the_import(config: ImportConfig):
    with pytest.raises(ImportFailed):
        await run_import(b"%PDF-1.7 broken", config, artifact_service([]), replying())


async def test_each_run_records_its_config_version(config: ImportConfig):
    with collect_runs() as runs:
        await run_import(
            PDF, config, artifact_service([]), replying(answer("Engineer"))
        )

    assert runs.traced_runs[0].extra["metadata"]["import_config"] == config.version
    assert config.model_copy(update={"prompt": "Read it."}).version != config.version
