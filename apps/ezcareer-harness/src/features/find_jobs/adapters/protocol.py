from typing import Any, Protocol

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


class SearchProtocol(Protocol):
    query: type[BaseModel]
    """The source's own search arguments; a field named like another source's
    must have the same type, since search_jobs shares it"""

    usage: str
    """What a search costs, for search_jobs' description"""

    async def search(self, query: Any) -> SearchResult:
        """Runs one search with a query of the source's own type, as postings any
        source can return; raises SourceUnavailable when it can't run"""
        ...
