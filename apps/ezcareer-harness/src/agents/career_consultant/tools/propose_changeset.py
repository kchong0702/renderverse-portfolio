import json
from functools import partial, update_wrapper
from uuid import NAMESPACE_OID, uuid5

from document_schema import Changeset
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.func import task
from langgraph.types import Command, interrupt
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model

from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.checks import check_changeset, cited_values, sources
from src.agents.career_consultant.page_fit import fit_pages
from src.agents.career_consultant.types import ChangesetProposed
from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import PageCountPreservationSettings
from src.core.errors import ExecuteError
from src.shared.checks import check_round
from src.shared.tool_artifact import StepDetail
from src.shared.tool_error import ToolError


def _citing(changeset: Changeset, facts: dict[str, str]) -> StepDetail:
    """The first profile fact the edits cite, and how many more they cite"""
    cited = [
        *dict.fromkeys(
            source
            for edit in changeset.edits
            for _, value in cited_values(edit.model_dump(mode="json"), "")
            for source in value.src
            if source in facts
        )
    ]
    if not cited:
        return {}
    more = f" and {len(cited) - 1} more" if len(cited) > 1 else ""
    return {"step_detail": f"citing {facts[cited[0]]}{more}"}


@task
async def _run_fit_pages(
    artifact_service: ArtifactServiceClient,
    page_count_preservation: PageCountPreservationSettings,
    changeset: Changeset,
    state: CareerConsultantState,
) -> str | Changeset:
    """The changeset's check errors as JSON, or once it passes, the changeset fitted
    to the page count when enabled; a task, so a resume can reuse it"""
    errors = check_round(check_changeset(state["document"], changeset, sources(state)))[
        "errors"
    ]
    if errors:
        return json.dumps([error.model_dump() for error in errors])
    if not page_count_preservation.enabled:
        return changeset
    return await fit_pages(
        state["document"],
        changeset,
        artifact_service,
        page_count_preservation.max_bullet_trims,
    )


async def _propose_changeset(
    artifact_service: ArtifactServiceClient,
    page_count_preservation: PageCountPreservationSettings,
    changeset: Changeset,
    runtime: ToolRuntime[None, CareerConsultantState],
) -> Command | ToolMessage | str:
    """Proposes a changeset to the user. Returns "proposed", or a JSON list of errors,
    each with its rule, edit path and what to fix; fix every one and propose again."""
    if runtime.state.get("document_read_for") != runtime.state["document_id"]:
        return ToolMessage(
            "Read the document with read_document first, then propose the changeset",
            name="propose_changeset",
            tool_call_id=runtime.tool_call_id,
            status="error",
        )
    changeset = await _run_fit_pages(
        artifact_service,
        page_count_preservation,
        changeset.model_copy(
            update={
                "id": uuid5(NAMESPACE_OID, runtime.tool_call_id).hex,
                "agent": "career-consultant",
            }
        ),
        runtime.state,
    )
    if isinstance(changeset, str):
        return changeset
    try:
        proposed_changeset = TypeAdapter(ChangesetProposed | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "propose_changeset",
                    "document_id": runtime.state["document_id"],
                    "changeset": changeset.model_dump(mode="json"),
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The changeset wasn't proposed: {error}") from error
    if isinstance(proposed_changeset, ToolError):
        return json.dumps([proposed_changeset.model_dump()])
    return Command(
        update={
            "changeset": changeset,
            "messages": [
                ToolMessage(
                    "proposed",
                    name="propose_changeset",
                    tool_call_id=runtime.tool_call_id,
                    artifact={
                        "name": "changeset",
                        "data": {
                            "document_id": runtime.state["document_id"],
                            "changeset_id": proposed_changeset.changeset_id,
                        },
                        **_citing(
                            changeset,
                            {
                                f"fact:{fact.id}": fact.text
                                for fact in runtime.state["profile_facts"]
                            },
                        ),
                    },
                )
            ],
        }
    )


def propose_changeset_tool(
    artifact_service: ArtifactServiceClient,
    page_count_preservation: PageCountPreservationSettings,
) -> BaseTool:
    """propose_changeset: checks a changeset, fits it to the page count when enabled,
    and asks ops-api to save it"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_propose_changeset, artifact_service, page_count_preservation),
            _propose_changeset,
        ),
        name="propose_changeset",
        args_schema=create_model(
            "ProposeChangesetArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            changeset=(Changeset, Field(description="The edits to propose")),
            runtime=(
                ToolRuntime[None, CareerConsultantState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
        ),
    )
