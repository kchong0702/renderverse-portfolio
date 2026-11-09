import json

from document_schema import Changeset
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.agents.career_consultant import CareerConsultantState
from src.features.write_document.checks import check_changeset, sources


@tool
def validate_changeset(
    changeset: Changeset, runtime: ToolRuntime[None, CareerConsultantState]
) -> str:
    """Checks a changeset before you answer with it. Returns "passes", or a JSON list
    of errors, each with its rule, edit path and what to fix; fix every one."""
    errors = check_changeset(
        runtime.state["document"], changeset, sources(runtime.state)
    )
    return json.dumps([error.model_dump() for error in errors]) if errors else "passes"
