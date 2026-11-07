import json
from base64 import b64encode
from pathlib import Path

from scripts import probe
from src.core.config import reload_settings
from src.features.import_document import ImportConfig, run_import
from src.shared.checks.resume import Check
from tests.fakes import artifact_service, replying
from tests.features.import_document.test_import import PDF, answer


def test_a_harness_folder_sets_the_config(tmp_path: Path):
    (tmp_path / "structure.md").write_text("Read the résumé.")
    (tmp_path / "flow.yaml").write_text(
        "family: claude\nmodel: claude-haiku-5-5\nrounds: 2\nchecks: [schema, verbatim]\n"
    )

    config = ImportConfig.load(tmp_path)

    assert (config.family, config.model, config.prompt) == (
        "claude",
        "claude-haiku-5-5",
        "Read the résumé.",
    )
    assert (config.recursion_limit, config.checks) == (
        6,
        (Check.SCHEMA, Check.VERBATIM),
    )


def test_the_probe_runs_the_import_from_config_toml(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("AIGW_UPSTREAM_URL", "http://gateway.test/v1")
    monkeypatch.setenv("AIGW_PASSTHROUGH_KEY", "test-key")
    task = tmp_path / "task.json"
    task.write_text(json.dumps({"file": b64encode(b"%PDF-1.7 broken").decode()}))

    probe.main(["--flow", "import", "--task", str(task)])

    result = json.loads(capsys.readouterr().out)
    assert result["error"] == "ImportFailed: the file is not a readable PDF"
    assert result["harness_hash"] == probe.harness_hash(reload_settings())


def test_a_prompt_edit_changes_the_harness_hash(tmp_path: Path, monkeypatch):
    harness = tmp_path / "harness"
    harness.mkdir()
    (harness / "flow.yaml").write_text(
        "family: glm\nmodel: glm-5.3\nrounds: 4\nchecks: [schema]\n"
    )
    (harness / "structure.md").write_text("Read the résumé.")
    config = tmp_path / "config.toml"
    config.write_text(f'[[flows]]\nname = "import"\npath = "{harness}"\n')
    monkeypatch.setenv("EZCAREER_HARNESS_CONFIG", str(config))

    before = probe.harness_hash(reload_settings())
    (harness / "structure.md").write_text("Read the résumé carefully.")

    assert probe.harness_hash(reload_settings()) != before


async def test_a_probe_records_each_round_of_import_checks(config: ImportConfig):
    async def flow(task: object) -> object:
        model = replying(answer("Wrong"), answer("Engineer"))
        return await run_import(PDF, config, artifact_service([]), model)

    result = await probe.probe(flow, None)

    assert result["error"] is None
    assert [[e["rule"] for e in r] for r in result["trace"]["check_rounds"]] == [
        ["verbatim", "coverage"],
        [],
    ]
