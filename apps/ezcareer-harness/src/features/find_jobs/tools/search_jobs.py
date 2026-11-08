from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo

from src.agents.job_finder import JobFinderState
from src.features.find_jobs.adapters import (
    SearchProtocol,
    SearchResult,
    SourceUnavailable,
)
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting


class _SearchJobsContent(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    jobs: list[JobPosting]
    """The user's jobs, newest first"""

    requests_left: int | None
    """Fewest requests any source has left, if one says"""

    unavailable: list[str]
    """Why each source that couldn't search failed"""


async def _search_jobs(
    sources: Sequence[SearchProtocol],
    runtime: ToolRuntime[None, JobFinderState],
    **given: object,
) -> tuple[str, list[JobPosting]]:
    """Searches job postings, newest first, with each job once and without jobs
    that break the user's preferences"""
    results: list[SearchResult] = []
    unavailable: list[str] = []
    for source in sources:
        try:
            results.append(
                await source.search(
                    source.query.model_validate(
                        {
                            name: value
                            for name, value in given.items()
                            if name in source.query.model_fields
                        }
                    )
                )
            )
        except SourceUnavailable as error:
            unavailable.append(str(error))
    if unavailable and not results:
        raise ToolException("; ".join(unavailable))
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        (posting for result in results for posting in result.postings),
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        unique.setdefault(
            (posting.title.casefold(), posting.company.casefold(), posting.location),
            posting,
        )
    jobs = [
        job
        for job in unique.values()
        if not broken_filters(job, runtime.state["preferences"])
    ]
    return _SearchJobsContent(
        jobs=jobs,
        requests_left=min(
            (r.requests_left for r in results if r.requests_left is not None),
            default=None,
        ),
        unavailable=unavailable,
    ).model_dump_json(), jobs


def search_jobs_tool(sources: Sequence[SearchProtocol]) -> BaseTool:
    """search_jobs over the given job sources, each given only its own arguments"""
    fields: dict[str, FieldInfo] = {}
    for source in sources:
        for name, field in source.query.model_fields.items():
            if name in fields and fields[name].annotation != field.annotation:
                raise ValueError(f"Job sources disagree on the type of {name!r}")
            fields.setdefault(name, field)
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_search_jobs, sources), _search_jobs),
        name="search_jobs",
        args_schema=create_model(
            "SearchJobsArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, JobFinderState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            **{name: (field.annotation, field) for name, field in fields.items()},
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
