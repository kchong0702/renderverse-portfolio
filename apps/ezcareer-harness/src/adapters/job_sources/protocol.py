from typing import Protocol

from pydantic import BaseModel, ConfigDict

from src.shared.jobs import JobPosting


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    postings: list[JobPosting]
    """The jobs found, in the source's order"""

    requests_left: int | None = None
    """Requests the source has left, if it says"""


class SearchProtocol[Q: BaseModel](Protocol):
    query: type[Q]
    """The source's own search arguments"""

    async def search(self, query: Q) -> SearchResult:
        """Runs one search; raises SourceUnavailable when the source can't search"""
        ...
