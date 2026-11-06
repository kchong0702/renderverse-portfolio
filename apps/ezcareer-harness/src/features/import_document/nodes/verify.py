from typing import Any

from langgraph.runtime import Runtime

from src.features.import_document.state import ImportContext, ImportState
from src.shared.checks import validate_resume


def verify(state: ImportState, runtime: Runtime[ImportContext]) -> dict[str, Any]:
    """Runs the import checks and writes any errors up for the LLM"""
    errors = validate_resume(
        state["reply"], state["lines"], runtime.context.config.checks
    )
    return {
        "rounds": [errors],
        "fix_summary": "\n".join(
            f"- {error.check} at {error.path}: {error.message}" for error in errors
        ),
    }
