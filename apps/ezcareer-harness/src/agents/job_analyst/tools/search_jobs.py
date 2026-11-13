from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool, ToolException
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from src.agents.job_analyst.state import JobAnalystState
from src.core.errors import ExecuteError
from src.shared.jobs import FoundJobs, PostedWithin, job_key
from src.shared.profile import CountryCode
from src.shared.run_context import RunContext
from src.shared.tool_error import ToolError


class _JobQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    query: str
    """A job title with at most one skill, such as "backend engineer python"; each
    extra word narrows the search"""

    location: str | None = None
    """City or region to search in, such as London; leave it out to search the
    whole country"""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB; a search without it is not
    worldwide"""

    remote_only: bool = False
    """Return only remote jobs"""

    posted_within: PostedWithin | None = PostedWithin.WEEK
    """How recent the jobs must be; null takes jobs of any age"""

    employment_types: list[
        Literal["full_time", "part_time", "contract", "internship"]
    ] = Field(default_factory=list)
    """Kinds of employment to keep; empty keeps every kind"""

    job_requirements: list[
        Literal[
            "under_3_years_experience",
            "more_than_3_years_experience",
            "no_experience",
            "no_degree",
        ]
    ] = Field(default_factory=list)
    """Experience or education requirements to keep; empty keeps every job"""

    radius_km: int | None = Field(default=None, gt=0)
    """How far from the location a job may be"""


class _SearchJobsArgs(_JobQuery):
    model_config = ConfigDict(
        extra="forbid", arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    runtime: ToolRuntime[RunContext | None, JobAnalystState]
    """The agent's state and the run's context"""


async def _search_jobs(
    runtime: ToolRuntime[RunContext | None, JobAnalystState], **given: object
) -> tuple[str, FoundJobs]:
    """Asks Ops for 10 jobs, the user's own search fields over the agent's; the model
    sees each job under its job_key, and the artifact keeps the source's ids"""
    query = _JobQuery.model_validate(given)
    if search := runtime.state.get("search"):
        query = query.model_copy(
            update={
                "query": search.query or query.query,
                "location": search.location or query.location,
                "posted_within": search.posted_within or query.posted_within,
            }
        )
    try:
        found = TypeAdapter(FoundJobs | ToolError).validate_python(
            interrupt(
                {
                    "execute_tool": "job_search",
                    **query.model_dump(mode="json"),
                    "max_jobs": 10,
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The job search didn't load: {error}") from error
    if isinstance(found, ToolError):
        raise ToolException(found.error)
    shown = found.model_copy(
        update={
            "jobs": [j.model_copy(update={"id": job_key(j.id)}) for j in found.jobs]
        }
    )
    return shown.model_dump_json(), found


search_jobs = StructuredTool.from_function(
    coroutine=_search_jobs,
    name="search_jobs",
    args_schema=_SearchJobsArgs,
    response_format="content_and_artifact",
    handle_tool_error=True,
)
