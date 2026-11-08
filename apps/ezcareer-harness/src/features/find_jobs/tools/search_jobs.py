import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model
from pydantic.fields import FieldInfo

from src.agents.job_finder import JobFinderState
from src.features.find_jobs.adapters import (
    SearchProtocol,
    SearchResult,
    SourceUnavailable,
)
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting
from src.shared.models import Preferences

DESCRIPTION = (
    "Search job postings, newest first, with the same job from several sites "
    "listed once and jobs that break the user's preferences left out."
)
"""What search_jobs does, before each source says what a search costs"""


def _arguments(sources: Sequence[SearchProtocol]) -> type[BaseModel]:
    """search_jobs' arguments: every source's own fields, one per name, so sources
    share what they have in common, plus the injected agent state"""
    fields: dict[str, FieldInfo] = {}
    for source in sources:
        for name, field in source.query.model_fields.items():
            if name in fields and fields[name].annotation != field.annotation:
                raise ValueError(f"Job sources disagree on the type of {name!r}")
            fields.setdefault(name, field)
    return create_model(
        "SearchJobsArgs",
        __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
        runtime=(
            ToolRuntime[None, JobFinderState],
            Field(
                description="The agent's state, injected by the agent and never set by the model"
            ),
        ),
        **{name: (field.annotation, field) for name, field in fields.items()},
    )


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


def search_jobs_tool(sources: Sequence[SearchProtocol]) -> BaseTool:
    """search_jobs over the given job sources, each given only its own arguments"""

    async def search_jobs(
        runtime: ToolRuntime[None, JobFinderState], **given: Any
    ) -> tuple[str, list[JobPosting]]:
        """Searches every source and returns the user's jobs with each source's notes"""
        results: list[SearchResult] = []
        unavailable: list[str] = []
        for source in sources:
            fields = source.query.model_fields
            query = source.query.model_validate(
                {name: value for name, value in given.items() if name in fields}
            )
            try:
                results.append(await source.search(query))
            except SourceUnavailable as error:
                unavailable.append(str(error))
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
        description=" ".join([DESCRIPTION, *(source.usage for source in sources)]),
        args_schema=_arguments(sources),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
