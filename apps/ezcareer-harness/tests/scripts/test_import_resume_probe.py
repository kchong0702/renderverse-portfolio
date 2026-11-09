import json
from base64 import b64encode
from functools import partial
from pathlib import Path

import httpx
import pytest

from scripts import probe
from src.core.config import reload_settings
from src.features.import_document import build_graph
from tests.features.import_document.test_extract import _artifact_service, _convert
from tests.features.import_document.test_import_graph import _model, _reply
from tests.features.write_document.test_write_document_graph import _print
from tests.pdfs import make_pdf


def test_the_probe_runs_the_import_from_config_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(_convert),
            base_url="http://artifact-service",
        )
    )
    task = tmp_path / "task.json"
    task.write_text(json.dumps({"file": b64encode(b"%PDF-1.7 broken").decode()}))

    probe.main(["--workflow", "import-resume", "--task", str(task)])

    result = json.loads(capsys.readouterr().out)
    assert result["error"] == "ImportFailed: the file is not a readable PDF"
    assert result["harness_hash"] == probe.harness_hash(reload_settings())


async def test_a_probe_runs_the_containers_import_graph_and_records_each_check_round():
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.import_document.import_resume_executable(
        graph=build_graph(
            _artifact_service(partial(_print, sent=[])),
            model=_model(_reply("Wrong"), _reply("Engineer")),
        )
    )

    result = await probe.probe(
        probe.WORKFLOWS["import-resume"],
        {
            "file": b64encode(
                make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])
            ).decode()
        },
    )

    assert result["error"] is None
    assert result["output"]["pdf"] == "JVBERg=="
    assert [[e["rule"] for e in r] for r in result["trace"]["check_rounds"]] == [
        ["verbatim", "coverage"],
        [],
    ]
