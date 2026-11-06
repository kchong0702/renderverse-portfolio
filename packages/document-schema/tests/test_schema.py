from document_schema import json_schemas


def test_the_json_schema_describes_each_field_for_the_agent() -> None:
    schemas = json_schemas()
    job = schemas["document"]["$defs"]["Job"]["properties"]

    assert set(schemas) == {"document"}
    assert job["role"]["description"] == "Job title"
