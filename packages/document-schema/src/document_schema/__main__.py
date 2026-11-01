import json

from document_schema import DOCUMENT_ADAPTER, RenderReport

schemas = {
    "document": DOCUMENT_ADAPTER.json_schema(),
    "render_report": RenderReport.model_json_schema(),
}
print(json.dumps(schemas, indent=2))
