from functools import partial, update_wrapper

from document_schema import TemplateSpec
from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import ConfigDict, Field, TypeAdapter, create_model

from src.agents.career_consultant.state import CareerConsultantState
from src.clients.artifact_service import ArtifactServiceClient


async def _list_design_options(
    artifact_service: ArtifactServiceClient,
    runtime: ToolRuntime[None, CareerConsultantState],
) -> str:
    """Lists the template specs an update_design edit can use for the document's
    kind; only for changes to how the document looks"""
    return (
        TypeAdapter(list[TemplateSpec])
        .dump_json(
            await artifact_service.list_templates(runtime.state["document"].kind)
        )
        .decode()
    )


def list_design_options_tool(artifact_service: ArtifactServiceClient) -> BaseTool:
    """list_design_options over artifact_service's templates"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_list_design_options, artifact_service), _list_design_options
        ),
        name="list_design_options",
        args_schema=create_model(
            "ListDesignOptionsArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, CareerConsultantState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
        ),
    )
