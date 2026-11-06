from typing import Any

from pydantic import TypeAdapter

from document_schema.changesets import Changeset
from document_schema.document import AnyDocument
from document_schema.report import Report
from document_schema.template import TemplateSpec


def json_schemas() -> dict[str, dict[str, Any]]:
    """The JSON Schema of each format, by name"""
    return {
        "document": TypeAdapter(AnyDocument).json_schema(),
        "changeset": Changeset.model_json_schema(),
        "report": Report.model_json_schema(),
        "template": TemplateSpec.model_json_schema(),
    }
