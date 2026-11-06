from typing import Any

from pydantic import TypeAdapter

from document_schema.document import AnyDocument


def json_schemas() -> dict[str, dict[str, Any]]:
    """The JSON Schema of each format, by name"""
    return {"document": TypeAdapter(AnyDocument).json_schema()}
