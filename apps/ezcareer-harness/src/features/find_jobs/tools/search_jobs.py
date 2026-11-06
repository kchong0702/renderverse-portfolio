from datetime import UTC, datetime

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, TypeAdapter

from src.core.config import get_settings
from src.features.find_jobs.schemas import JobPosting
from src.features.find_jobs.sources import search
from src.features.find_jobs.types import DatePosted
from src.shared.models import CountryCode


class SearchJobsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    query: str
    """Job title and key skills, with a city when the user wants one,
    such as "backend engineer python in London\""""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB"""

    remote_only: bool = False
    """Return only remote jobs"""

    date_posted: DatePosted = "week"
    """How recent the jobs must be"""


@tool(args_schema=SearchJobsArgs, response_format="content_and_artifact")
async def search_jobs(
    query: str,
    country: CountryCode | None = None,
    remote_only: bool = False,
    date_posted: DatePosted = "week",
) -> tuple[str, list[JobPosting]]:
    """Search job postings, newest first, with the same job from several
    sites listed once."""
    postings = await search(
        get_settings().jsearch, query, country, remote_only, date_posted
    )
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        postings,
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        key = (posting.title.casefold(), posting.company.casefold(), posting.location)
        unique.setdefault(key, posting)
    jobs = list(unique.values())
    return TypeAdapter(list[JobPosting]).dump_json(jobs).decode(), jobs
