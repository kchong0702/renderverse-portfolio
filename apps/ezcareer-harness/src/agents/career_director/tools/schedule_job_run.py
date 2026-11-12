from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import AwareDatetime, TypeAdapter, ValidationError

from src.agents.career_director.types import JobRunQueued
from src.core.errors import ExecuteError
from src.shared.fetch_failed import FetchFailed
from src.shared.jobs import JobSearch
from src.shared.tool_artifact import StepDetail


@tool(response_format="content_and_artifact")
def schedule_job_run(
    run_after: AwareDatetime | None = None, search: JobSearch | None = None
) -> tuple[str, StepDetail]:
    """Queues a background job search that finds and scores fresh jobs, as soon as a worker is free
    or from run_after (ISO 8601 with offset); search, when given, says what, where and how recent to look"""
    try:
        queued = TypeAdapter(JobRunQueued | FetchFailed).validate_python(
            interrupt(
                {
                    "fetch": "job_run",
                    "run_after": run_after.isoformat() if run_after else None,
                    "search": search.model_dump(mode="json") if search else None,
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The job run didn't queue: {error}") from error
    if isinstance(queued, FetchFailed):
        return f"No run was queued: {queued.error}", {}
    when = queued.run_after.strftime("%a %d %b %H:%M %Z")
    return f"Queued a job search to run from {when}.", {"step_detail": when}
