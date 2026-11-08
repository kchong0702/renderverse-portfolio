import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import Field, TypeAdapter

from src.features.find_jobs.adapters import JOB_SOURCES
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting
from src.shared.models import Preferences
from src.shared.tools import ProfileState

DESCRIPTION = (
    "Search job postings, newest first, with the same job from several sites "
    "listed once and jobs that break the user's preferences left out."
)
"""What search_jobs does, before each source says what a search costs"""


class JobSearchState(ProfileState):
    preferences: Preferences
    """What the user wants from a job, which search_jobs filters by"""


def _for_user(postings: list[JobPosting], preferences: Preferences) -> list[JobPosting]:
    """Postings newest first, each job once however many sites list it, without
    jobs that break the user's preferences"""
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        postings,
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        key = (posting.title.casefold(), posting.company.casefold(), posting.location)
        unique.setdefault(key, posting)
    return [job for job in unique.values() if not broken_filters(job, preferences)]


def search_jobs_tool(sources: Sequence[str]) -> BaseTool:
    """search_jobs over the job sources named, each given only its own arguments"""
    enabled = JOB_SOURCES.enable(sources)

    async def search_jobs(
        runtime: ToolRuntime[None, JobSearchState], **given: Any
    ) -> tuple[str, list[JobPosting]]:
        """Searches every source and returns the user's jobs with each source's notes"""
        results, unavailable = await enabled.run(given)
        if unavailable and not results:
            raise ToolException("; ".join(unavailable))
        jobs = _for_user(
            [posting for result in results for posting in result.postings],
            runtime.state["preferences"],
        )
        content = {
            "jobs": TypeAdapter(list[JobPosting]).dump_python(jobs, mode="json"),
            **{key: value for result in results for key, value in result.notes.items()},
            **({"unavailable": unavailable} if unavailable else {}),
        }
        return json.dumps(content), jobs

    return StructuredTool.from_function(
        coroutine=search_jobs,
        name="search_jobs",
        description=f"{DESCRIPTION} {enabled.usage}",
        args_schema=enabled.arguments(
            "SearchJobsArgs",
            runtime=(
                ToolRuntime[None, JobSearchState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
