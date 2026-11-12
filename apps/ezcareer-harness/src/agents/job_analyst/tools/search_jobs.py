from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo

from src.adapters.job_sources import (
    SearchProtocol,
    SearchResult,
    SourceUnavailable,
)
from src.agents.job_analyst.state import JobAnalystState
from src.shared.factory import Factory
from src.shared.jobs import JobPosting, broken_filters
from src.shared.run_context import RunContext


class _SearchJobsContent(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    jobs: list[JobPosting]
    """The user's jobs, newest first"""

    requests_left: int | None
    """Fewest requests any source has left, if one says"""

    failures: list[str]
    """Why each source that couldn't search failed"""


async def _search_jobs(
    sources: Sequence[SearchProtocol],
    runtime: ToolRuntime[RunContext | None, JobAnalystState],
    **given: object,
) -> tuple[str, SearchResult]:
    """Searches job postings, newest first, with each job once and without jobs
    that break the user's preferences"""
    results: list[SearchResult] = []
    failures: list[str] = []
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
                    ),
                    runtime.state.get("search"),
                    runtime.context,
                )
            )
        except SourceUnavailable as error:
            failures.append(str(error))
    if failures and not results:
        raise ToolException("; ".join(failures))
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
    quota = min(
        (result.quota for result in results if result.quota),
        key=lambda quota: quota.remaining,
        default=None,
    )
    return _SearchJobsContent(
        jobs=jobs,
        requests_left=quota and quota.remaining,
        failures=failures,
    ).model_dump_json(), SearchResult(postings=jobs, quota=quota)


def search_jobs_tool(
    job_sources: Factory[SearchProtocol], names: Sequence[str]
) -> BaseTool:
    """search_jobs over the job sources called names, each given only its own
    arguments"""
    sources = [job_sources.create(name) for name in names]
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
                ToolRuntime[RunContext | None, JobAnalystState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            **{name: (field.annotation, field) for name, field in fields.items()},
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
