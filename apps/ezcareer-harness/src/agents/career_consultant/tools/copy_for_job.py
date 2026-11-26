from uuid import NAMESPACE_OID, uuid5

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from pydantic import TypeAdapter, ValidationError

from src.agents.career_consultant.state import CareerConsultantState
from src.agents.career_consultant.types import CopiedForJob
from src.core.errors import ExecuteError
from src.shared.tool_error import ToolError


@tool
def copy_for_job(
    runtime: ToolRuntime[None, CareerConsultantState],
    job_id: str,
    start_over: bool = False,
) -> Command | str:
    """Moves you to the job's copy of your document, made the first time, with the
    posting; start_over starts the copy over from the document it was copied from"""
    try:
        copied = TypeAdapter(CopiedForJob | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "copy_for_job",
                    "document_id": runtime.state["desired_document_id"],
                    "job_id": job_id,
                    "start_over": start_over,
                    "copy_id": uuid5(NAMESPACE_OID, runtime.tool_call_id).hex,
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The document wasn't copied: {error}") from error
    if isinstance(copied, ToolError):
        return f"The document wasn't copied: {copied.error}"
    return Command(
        update={
            "desired_document_id": copied.document_id,
            "document": copied.document,
            "actual_document_id": copied.document_id,
            "pdf_lines": copied.pdf_lines,
            "messages": [
                ToolMessage(
                    "<document untrusted>\n"
                    + copied.model_dump_json(
                        include={
                            "document_id": True,
                            "document": True,
                            "pdf_lines": {"__all__": {"id", "text"}},
                        }
                    )
                    + f"\n</document>\n<job untrusted>\n{copied.job.model_dump_json()}\n</job>"
                    + (
                        "\nMade a new copy for the job."
                        if copied.made
                        else "\nUsing the job's existing copy."
                    )
                    + (
                        "\nThere was no copy to start over."
                        if start_over and copied.made
                        else ""
                    )
                    + (
                        "\nStarting over rejected the copy's pending proposal, which"
                        " no longer fit its draft."
                        if copied.rejected_changeset
                        else ""
                    ),
                    name="copy_for_job",
                    tool_call_id=runtime.tool_call_id,
                    artifact={"step_detail": copied.job.company or copied.job.title},
                )
            ],
        }
    )
