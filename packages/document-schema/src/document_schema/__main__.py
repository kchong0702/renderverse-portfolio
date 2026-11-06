import json

from pydantic import TypeAdapter

from document_schema import AnyDocument

schemas = {"document": TypeAdapter(AnyDocument).json_schema()}
print(json.dumps(schemas, indent=2))
