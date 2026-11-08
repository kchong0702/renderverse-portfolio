from datetime import UTC, datetime

import httpx
from langchain.tools import ToolRuntime
from langchain_core.tools import ToolException, tool
from pydantic import BaseModel, ConfigDict, TypeAdapter

from src.core.config import get_settings
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting
from src.features.find_jobs.sources import search
from src.features.find_jobs.types import DatePosted
from src.shared.models import CountryCode, Preferences
from src.shared.tools import ProfileState


class JobSearchState(ProfileState):
    preferences: Preferences
    """What the user wants from a job, which search_jobs filters by"""


class SearchJobsArgs(BaseModel):
    """Search job postings, newest first, with the same job from several sites
    listed once and jobs that break the user's preferences left out."""

    model_config = ConfigDict(
        extra="forbid", arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    query: str
    """Job title and key skills, with a city when the user wants one,
    such as "backend engineer python in London\""""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB"""

    remote_only: bool = False
    """Return only remote jobs"""

    date_posted: DatePosted = "week"
    """How recent the jobs must be"""

    runtime: ToolRuntime[None, JobSearchState]
    """The agent's state, injected by the agent and never set by the model"""


@tool(args_schema=SearchJobsArgs, response_format="content_and_artifact")
async def search_jobs(
    query: str,
    country: CountryCode | None = None,
    remote_only: bool = False,
    date_posted: DatePosted = "week",
    *,
    runtime: ToolRuntime[None, JobSearchState],
) -> tuple[str, list[JobPosting]]:
    """Search job postings, newest first, with the same job from several sites
    listed once and jobs that break the user's preferences left out."""
    try:
        postings = await search(
            get_settings().jsearch, query, country, remote_only, date_posted
        )
    except httpx.HTTPError as error:
        raise ToolException(
            f"Job search failed, try again later: {type(error).__name__} {error}"
        ) from error
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        postings,
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        key = (posting.title.casefold(), posting.company.casefold(), posting.location)
        unique.setdefault(key, posting)
    preferences = runtime.state["preferences"]
    jobs = [job for job in unique.values() if not broken_filters(job, preferences)]
    return TypeAdapter(list[JobPosting]).dump_json(jobs).decode(), jobs


search_jobs.handle_tool_error = True
