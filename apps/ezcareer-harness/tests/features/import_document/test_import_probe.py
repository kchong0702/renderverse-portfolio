import json
import shutil
from base64 import b64encode
from pathlib import Path

from src import run
from src.features.import_document import ImportConfig, run_import
from tests.fakes import artifact_service, replying
from tests.features.import_document.test_import import PDF, answer


def test_a_probe_runs_the_import_with_a_harness_folder(tmp_path: Path, capsys):
    harness = tmp_path / "harness"
    shutil.copytree(
        Path(run.__file__).parent / "features/import_document/harness", harness
    )
    (harness / "structure.md").write_text("Read the résumé.")
    task = tmp_path / "task.json"
    task.write_text(json.dumps({"file": b64encode(b"%PDF-1.7 broken").decode()}))

    run.main(["--flow", "import", "--harness", str(harness), "--task", str(task)])

    result = json.loads(capsys.readouterr().out)
    assert result["error"] == "ImportFailed: the file is not a readable PDF"
    assert result["trace"]["harness_hashes"] == [ImportConfig.load(harness).hash]


async def test_a_probe_records_each_round_of_import_checks(config: ImportConfig):
    async def flow(harness: Path, task: object) -> object:
        model = replying(answer("Wrong"), answer("Engineer"))
        return await run_import(PDF, config, artifact_service([]), model)

    result = await run.run(flow, Path("unused"), None)

    assert result["error"] is None
    assert [[e["rule"] for e in r] for r in result["trace"]["check_rounds"]] == [
        ["verbatim", "coverage"],
        [],
    ]
    assert result["trace"]["harness_hashes"] == [config.hash]
