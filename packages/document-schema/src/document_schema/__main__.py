import json

from pydantic import TypeAdapter

from document_schema import AnyDocument, Changeset, Report

schemas = {
    "document": TypeAdapter(AnyDocument).json_schema(),
    "changeset": Changeset.model_json_schema(),
    "report": Report.model_json_schema(),
}
print(json.dumps(schemas, indent=2))
