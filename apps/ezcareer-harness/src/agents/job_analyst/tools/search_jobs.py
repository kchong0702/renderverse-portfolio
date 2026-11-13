from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool, ToolException
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from src.agents.job_analyst.state import JobAnalystState
from src.core.errors import ExecuteError
from src.shared.jobs import FoundJobs, PostedWithin
from src.shared.profile import CountryCode
from src.shared.run_context import RunContext
from src.shared.tool_error import ToolError


class _JobQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    query: str
    """Job titles and key skills, such as "backend engineer python\""""

    location: str | None = None
    """City or region to search in, such as London; leave it out to search the
    whole country"""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB"""

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

    max_jobs: int = Field(default=30, ge=10, le=50, multiple_of=10)
    """How many jobs to fetch"""


class _SearchJobsArgs(_JobQuery):
    model_config = ConfigDict(
        extra="forbid", arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    runtime: ToolRuntime[RunContext | None, JobAnalystState]
    """The agent's state and the run's context"""


async def _search_jobs(
    runtime: ToolRuntime[RunContext | None, JobAnalystState], **given: object
) -> tuple[str, FoundJobs]:
    """Asks Ops to search for jobs, with the user's own search fields over the
    agent's"""
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
            interrupt({"execute_tool": "job_search", **query.model_dump(mode="json")})
        )
    except ValidationError as error:
        raise ExecuteError(f"The job search didn't load: {error}") from error
    if isinstance(found, ToolError):
        raise ToolException(found.error)
    return found.model_dump_json(), found


search_jobs = StructuredTool.from_function(
    coroutine=_search_jobs,
    name="search_jobs",
    args_schema=_SearchJobsArgs,
    response_format="content_and_artifact",
    handle_tool_error=True,
)
