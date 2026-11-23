import json
from functools import partial, update_wrapper

from document_schema import Changeset
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import ConfigDict, Field, create_model

from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.checks import check_changeset, cited_values, sources
from src.agents.career_consultant.page_fit import fit_pages
from src.clients.artifact_service import ArtifactServiceClient
from src.shared.checks import check_round
from src.shared.tool_artifact import StepDetail


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


async def _propose_changeset(
    artifact_service: ArtifactServiceClient,
    trims: int,
    changeset: Changeset,
    runtime: ToolRuntime[None, CareerConsultantState],
) -> Command | str:
    """Proposes a changeset to the user. Returns "proposed", or a JSON list of errors,
    each with its rule, edit path and what to fix; fix every one and propose again."""
    errors = check_round(
        check_changeset(runtime.state["document"], changeset, sources(runtime.state))
    )["errors"]
    if errors:
        return json.dumps([error.model_dump() for error in errors])
    changeset = await fit_pages(
        runtime.state["document"], changeset, artifact_service, trims
    )
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
                            "document_id": runtime.state.get("document_id"),
                            "changeset": changeset.model_dump(mode="json"),
                        },
                        **_citing(
                            changeset,
                            {
                                f"fact:{fact.id}": fact.text
                                for fact in runtime.state["facts"]
                            },
                        ),
                    },
                )
            ],
        }
    )


def propose_changeset_tool(
    artifact_service: ArtifactServiceClient, trims: int
) -> BaseTool:
    """propose_changeset, which checks a changeset and, once it passes, prints it
    through artifact_service and deletes up to trims bullets to keep the page count"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_propose_changeset, artifact_service, trims), _propose_changeset
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
