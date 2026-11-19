from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import FoundSavedJobs, JobStatus
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail


@tool(response_format="content_and_artifact")
def find_saved_jobs(
    company: str | None = None, status: JobStatus | None = None
) -> tuple[str, StepDetail]:
    """Finds the jobs on the user's Jobs page, those the job agent picked and those
    they saved, by part of a company's name, a status or both, with how many have
    each status; pass status dismissed for the jobs they hid"""
    try:
        found = FoundSavedJobs.model_validate(
            interrupt(
                {"execute_tool": "saved_jobs", "company": company, "status": status}
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The saved jobs didn't load: {error}") from error
    count = len(found.jobs)
    return to_json(
        {
            "total": sum(found.by_status.values()),
            "by_status": found.by_status,
            "jobs": found.jobs,
        }
    ).decode(), {"step_detail": f"{count} jobs" if count != 1 else "1 job"}
