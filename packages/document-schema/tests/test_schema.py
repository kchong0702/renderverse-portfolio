from __future__ import annotations

import json
import subprocess
import sys

from document_schema import Document


def test_cli_prints_the_document_and_render_report_schemas() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "document_schema"],
        capture_output=True,
        text=True,
        check=True,
    )

    schemas = json.loads(result.stdout)

    assert set(schemas) == {"document", "render_report"}
    assert {"Content", "Template", "Presentation"} <= set(schemas["document"]["$defs"])
    assert schemas["render_report"]["title"] == "RenderReport"
    assert "Overflow" in schemas["render_report"]["$defs"]


def test_field_docstrings_become_schema_descriptions() -> None:
    value = Document.model_json_schema()["$defs"]["Value"]

    assert value["properties"]["text"]["description"] == "Text as shown in the document"
