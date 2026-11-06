import json
import subprocess
import sys


def test_the_exported_schema_describes_each_field_for_the_agent() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "document_schema"],
        capture_output=True,
        text=True,
        check=True,
    )

    schemas = json.loads(out.stdout)
    job = schemas["document"]["$defs"]["Job"]["properties"]

    assert set(schemas) == {"document"}
    assert job["role"]["description"] == "Job title"
