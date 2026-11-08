import json

from document_schema import Changeset
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.agents.career_consultant import CareerConsultantState
from src.features.write_document.checks import check_changeset


@tool
def validate_changeset(
    changeset: Changeset, runtime: ToolRuntime[None, CareerConsultantState]
) -> str:
    """Checks a changeset before you answer with it. Returns "passes", or a JSON list
    of errors, each with its rule, edit path and what to fix; fix every one."""
    state = runtime.state
    errors = check_changeset(
        state["document"],
        changeset,
        {line.id: line.text for line in state["lines"]}
        | {f"fact:{fact.id}": fact.text for fact in state["facts"]},
    )
    return json.dumps([error.model_dump() for error in errors]) if errors else "passes"
