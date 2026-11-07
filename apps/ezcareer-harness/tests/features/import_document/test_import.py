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
        [Check.VERBATIM, Check.COVERAGE],
        [],
    ]
    system, human = model.prompts[1]
    assert system.content == model.prompts[0][0].content
    data = json.loads(human.content)
    assert data["previous_reply"] == answer("Engineering lead")
    assert [(e["rule"], e["at"]) for e in data["errors"]] == [
        ("verbatim", "content/blocks/profile/headline"),
        ("coverage", "content"),
    ]
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
    assert result.config_hash == config.hash


async def test_an_import_that_never_passes_fails_after_its_rounds(config: ImportConfig):
    model = replying(*[answer("Wrong")] * 10)
    requests: list[httpx.Request] = []

    with pytest.raises(ImportFailed, match="couldn't read this file"):
        await run_import(
            PDF,
            config.model_copy(update={"rounds": 2}),
            artifact_service(requests),
            model,
        )

    assert len(model.prompts) == 2
    assert requests == []


async def test_the_last_round_is_checked(config: ImportConfig):
    model = replying(answer("Wrong"), answer("Engineer"))

    result = await run_import(
        PDF, config.model_copy(update={"rounds": 2}), artifact_service([]), model
    )

    assert len(result.rounds) == 2


async def test_a_reply_without_the_tool_gets_another_round(config: ImportConfig):
    result = await run_import(
        PDF, config, artifact_service([]), replying(None, answer("Engineer"))
    )

    assert [errors[0].rule for errors in result.rounds[:1]] == ["schema"]
    assert result.rounds[-1] == []


async def test_a_photo_without_its_file_gets_another_round(config: ImportConfig):
    photo = answer("Engineer")
    photo["content"]["blocks"].append(
        {"kind": "photo", "id": "photo", "file": "a" * 64}
    )

    result = await run_import(
        PDF, config, artifact_service([]), replying(photo, answer("Engineer"))
    )

    [error] = result.rounds[0]
    assert (error.rule, "files not in assets" in error.message) == ("schema", True)


async def test_a_failed_render_fails_the_import(config: ImportConfig):
    with pytest.raises(ImportFailed, match="couldn't print the draft"):
        await run_import(
            PDF, config, artifact_service([], status=422), replying(answer("Engineer"))
        )


async def test_a_file_without_text_fails_the_import_with_its_reason(
    config: ImportConfig,
):
    with pytest.raises(ImportFailed, match="not a readable PDF"):
        await run_import(b"%PDF-1.7 broken", config, artifact_service([]), replying())


async def test_each_run_records_its_config_hash(config: ImportConfig):
    with collect_runs() as runs:
        await run_import(
            PDF, config, artifact_service([]), replying(answer("Engineer"))
        )

    assert runs.traced_runs[0].extra["metadata"]["import_config_hash"] == config.hash
    assert config.model_copy(update={"prompt": "Read it."}).hash != config.hash
