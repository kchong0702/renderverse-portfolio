import json
from datetime import UTC, datetime
from typing import Any

import httpx
from circuitbreaker import CircuitBreakerError, CircuitBreakerMonitor
from langchain.tools import ToolRuntime
from langchain_core.tools import ToolException, tool
from pydantic import ConfigDict, TypeAdapter

from src.core.config import get_settings
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting, JobQuery
from src.features.find_jobs.sources import search
from src.shared.models import Preferences
from src.shared.tools import ProfileState


class JobSearchState(ProfileState):
    preferences: Preferences
    """What the user wants from a job, which search_jobs filters by"""


class SearchJobsArgs(JobQuery):
    """Search job postings, newest first, with the same job from several sites
    listed once and jobs that break the user's preferences left out. Every 10 jobs
    costs one JSearch request from a budget of 200 a month; the result says how
    many are left."""

    model_config = ConfigDict(
        extra="forbid", arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    runtime: ToolRuntime[None, JobSearchState]
    """The agent's state, injected by the agent and never set by the model"""


@tool(args_schema=SearchJobsArgs, response_format="content_and_artifact")
async def search_jobs(
    runtime: ToolRuntime[None, JobSearchState], **query: Any
) -> tuple[str, list[JobPosting]]:
    """Search job postings, newest first, with the same job from several sites
    listed once and jobs that break the user's preferences left out. Every 10 jobs
    costs one JSearch request from a budget of 200 a month; the result says how
    many are left."""
    try:
        result = await search(get_settings().jsearch, JobQuery(**query))
    except CircuitBreakerError as error:
        raise ToolException(
            f"Job search is paused after repeated failures; try again in "
            f"{CircuitBreakerMonitor.get('jsearch').open_remaining:.0f}s"
        ) from error
    except httpx.HTTPError as error:
        raise ToolException(
            f"Job search failed, try again later: {type(error).__name__} {error}"
        ) from error
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        result.postings,
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        key = (posting.title.casefold(), posting.company.casefold(), posting.location)
        unique.setdefault(key, posting)
    preferences = runtime.state["preferences"]
    jobs = [job for job in unique.values() if not broken_filters(job, preferences)]
    content = {
        "jobs": TypeAdapter(list[JobPosting]).dump_python(jobs, mode="json"),
        "jsearch_requests_left_this_month": result.requests_left,
    }
    return json.dumps(content), jobs


search_jobs.handle_tool_error = True
