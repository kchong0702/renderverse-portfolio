from typing import Any

from document_schema import DocumentKind, ResumeDocument
from langgraph.runtime import Runtime

from src.features.import_document.state import ImportContext, ImportState
from src.shared.checks import validate_resume
from src.shared.models import ResumeImport


async def verify(state: ImportState, runtime: Runtime[ImportContext]) -> dict[str, Any]:
    """Runs the import checks, then prints the draft once they pass"""
    config = runtime.context.config
    errors = validate_resume(state["reply"], state["lines"], config.checks)
    if errors:
        return {
            "rounds": [errors],
            "fix_summary": "\n".join(
                f"- {error.check} at {error.path}: {error.message}" for error in errors
            ),
        }
    document = ResumeDocument(
        kind=DocumentKind.RESUME,
        content=ResumeImport.model_validate(state["reply"]).content,
    )
    rendered = await runtime.context.artifacts.render(
        document, config.template(document.design.template), assets={}
    )
    return {
        "rounds": [[]],
        "document": document,
        "pdf": rendered.pdf,
        "report": rendered.report,
    }
