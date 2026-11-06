from typing import Any

from langgraph.runtime import Runtime

from src.features.import_document.state import ImportContext, ImportState
from src.shared.extraction import extract_lines, to_pdf


def extract(state: ImportState, runtime: Runtime[ImportContext]) -> dict[str, Any]:
    """Reads the uploaded file's text lines"""
    pdf = to_pdf(state["file"], runtime.context.config.soffice)
    return {"lines": extract_lines(pdf)}
