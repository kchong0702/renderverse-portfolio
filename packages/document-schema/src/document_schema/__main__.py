import json

from document_schema import Document, RenderReport

schemas = {
    "document": Document.model_json_schema(),
    "render_report": RenderReport.model_json_schema(),
}
print(json.dumps(schemas, indent=2))
