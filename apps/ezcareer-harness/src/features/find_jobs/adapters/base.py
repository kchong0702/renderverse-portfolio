from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from src.features.find_jobs.schemas import JobPosting


class SourceUnavailable(Exception):
    """A job source can't search right now; the message says why and for how long"""


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    postings: list[JobPosting]
    """The jobs found, in the source's order"""

    notes: dict[str, JsonValue] = Field(default_factory=dict)
    """What the agent should know about the source, such as its requests left"""


class JobAdapter(BaseModel):
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    name: str
    """The name config.toml's job_sources enables it by, such as jsearch"""

    query: type[BaseModel]
    """The source's own search arguments; a field named like another source's
    must mean the same and have the same type"""

    usage: str
    """What a search costs, for search_jobs' description"""

    search: Callable[[Any], Awaitable[SearchResult]]
    """Runs one search with a query of the source's own type"""
