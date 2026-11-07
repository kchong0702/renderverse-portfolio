import json
from pathlib import Path

import pytest

from scripts import probe
from src.agents import builder
from src.features.write_document import service
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_career_consultant import (
    BAD_EDIT,
    GOOD_EDIT,
    _call,
    _changeset,
)
from tests.features.write_document.test_edit_graph import _render

FIXTURES = Path(__file__).parents[1] / "features/write_document/fixtures"


def test_a_probe_runs_the_edit_flow_through_its_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    model = ScriptedChatModel(
        replies=[
            _call("Changeset", **_changeset(BAD_EDIT)),
            _call("Changeset", **_changeset(GOOD_EDIT)),
        ]
    )
    monkeypatch.setattr(builder, "chat_model", lambda family, name: model)
    monkeypatch.setattr(service, "artifact_service_render", lambda: _render)
    task = tmp_path / "task.json"
    task.write_text(
        json.dumps(
            {
                "request": "Mention my Kubernetes work",
                "document": json.loads((FIXTURES / "resume.json").read_text()),
                "lines": [
                    {**line, "page": 1, "x0": 0, "top": 0, "x1": 1, "bottom": 1}
                    for line in json.loads((FIXTURES / "lines.json").read_text())
                ],
                "facts": json.loads((FIXTURES / "facts.json").read_text()),
            }
        )
    )
    out = tmp_path / "result.json"

    probe.main(["--flow", "edit", "--task", str(task), "--out", str(out)])

    result = json.loads(out.read_text())
    assert result["error"] is None
    assert [edit["path"] for edit in result["output"]["changeset"]["edits"]] == [
        GOOD_EDIT["path"]
    ]
    assert [
        [e["rule"] for e in errors] for errors in result["trace"]["check_rounds"]
    ] == [
        ["unsupported"],
        [],
    ]
