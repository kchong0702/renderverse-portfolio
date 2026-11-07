import json

from langchain_core.messages import HumanMessage

from src.features.write_document.profile import CHECKS
from src.features.write_document.state import EditGraphState, sources
from src.infrastructure import get_tracer
from src.shared.checks import CheckError


def validate(state: EditGraphState, checks: list[str]) -> dict:
    """Runs the named checks on the agent's changeset and sends any errors back
    to it"""
    changeset = state.get("structured_response")
    with get_tracer(__name__).start_as_current_span("checks") as span:
        errors = (
            [
                error
                for name in checks
                for error in CHECKS[name](state["document"], changeset, sources(state))
            ]
            if changeset
            else [
                CheckError(
                    rule="no_changeset",
                    at="answer",
                    message="you ended without a changeset; answer with the Changeset tool",
                )
            ]
        )
        found = json.dumps([error.model_dump() for error in errors])
        span.set_attribute("check.errors", found)
    if not errors:
        return {"errors": []}
    return {
        "errors": errors,
        "messages": [
            HumanMessage(
                f"The checks found these errors:\n{found}\n"
                "Fix exactly those edits and answer with the whole changeset again."
            )
        ],
    }
