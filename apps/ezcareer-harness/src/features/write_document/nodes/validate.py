import json

from langchain_core.messages import HumanMessage

from src.features.write_document.checks import check_changeset
from src.features.write_document.state import EditGraphState, sources
from src.infrastructure import get_tracer


def validate(state: EditGraphState) -> dict:
    """Checks the agent's changeset and sends any errors back to it"""
    with get_tracer(__name__).start_as_current_span("check_changeset") as span:
        errors = check_changeset(
            state["document"], state["structured_response"], sources(state)
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
