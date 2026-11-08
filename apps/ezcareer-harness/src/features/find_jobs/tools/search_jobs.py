import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model
from pydantic.fields import FieldInfo

from src.features.find_jobs.adapters import ADAPTERS, JobAdapter, SourceUnavailable
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


def _arguments(adapters: Sequence[JobAdapter]) -> type[BaseModel]:
    """search_jobs' arguments: every source's own arguments, with fields named alike
    merged into one, so sources share what they have in common"""
    fields: dict[str, FieldInfo] = {}
    for adapter in adapters:
        for name, field in adapter.query.model_fields.items():
            if name in fields and fields[name].annotation != field.annotation:
                raise ValueError(f"Job sources disagree on the type of {name!r}")
            fields.setdefault(name, field)
    return create_model(
        "SearchJobsArgs",
        __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
        runtime=(
            ToolRuntime[None, JobSearchState],
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


def search_jobs_tool(sources: Sequence[str]) -> BaseTool:
    """search_jobs over the job sources named, each given only its own arguments"""
    unknown = set(sources) - ADAPTERS.keys()
    if unknown:
        raise ValueError(
            f"Unknown job sources {sorted(unknown)}; known: {sorted(ADAPTERS)}"
        )
    adapters = [ADAPTERS[name] for name in sources]

    async def search_jobs(
        runtime: ToolRuntime[None, JobSearchState], **given: Any
    ) -> tuple[str, list[JobPosting]]:
        """Searches every source and returns the user's jobs with each source's notes"""
        postings: list[JobPosting] = []
        notes: dict[str, Any] = {}
        unavailable: list[str] = []
        for adapter in adapters:
            query = adapter.query.model_validate(
                {
                    name: value
                    for name, value in given.items()
                    if name in adapter.query.model_fields
                }
            )
            try:
                result = await adapter.search(query)
            except SourceUnavailable as error:
                unavailable.append(str(error))
                continue
            postings += result.postings
            notes |= result.notes
        if unavailable and not postings:
            raise ToolException("; ".join(unavailable))
        jobs = _for_user(postings, runtime.state["preferences"])
        content = {
            "jobs": TypeAdapter(list[JobPosting]).dump_python(jobs, mode="json"),
            **notes,
            **({"unavailable": unavailable} if unavailable else {}),
        }
        return json.dumps(content), jobs

    return StructuredTool.from_function(
        coroutine=search_jobs,
        name="search_jobs",
        description=" ".join([DESCRIPTION, *(adapter.usage for adapter in adapters)]),
        args_schema=_arguments(adapters),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
