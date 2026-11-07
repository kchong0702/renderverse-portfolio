import json
from typing import Literal

from document_schema import DocumentKind, ResumeDocument
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import ValidationError

from src.features.import_document.state import ImportContext, ImportState
from src.infrastructure import get_tracer
from src.shared.checks.resume import schema_errors, validate_resume
from src.shared.models.resume_import import ResumeImport


async def verify(
    state: ImportState, runtime: Runtime[ImportContext]
) -> Command[Literal["structure", "__end__"]]:
    """Runs the import checks and prints the draft once they pass; sends a failed
    reply back for another round while the config allows one"""
    config = runtime.context.config
    errors = validate_resume(state["reply"], state["lines"], config.checks)
    if not errors:
        try:
            document = ResumeDocument(
                kind=DocumentKind.RESUME,
                content=ResumeImport.model_validate(state["reply"]).content,
            )
        except ValidationError as error:
            errors = schema_errors(error)
    with get_tracer(__name__).start_as_current_span("check") as span:
        span.set_attribute(
            "check.errors", json.dumps([error.model_dump() for error in errors])
        )
    if errors:
        retry = len(state.get("rounds", [])) + 1 < config.rounds
        return Command(update={"rounds": [errors]}, goto="structure" if retry else END)
    rendered = await runtime.context.artifacts.render(
        document, config.template(document.design.template), assets={}
    )
    return Command(
        update={
            "rounds": [[]],
            "document": document,
            "pdf": rendered.pdf,
            "report": rendered.report,
        },
        goto=END,
    )
