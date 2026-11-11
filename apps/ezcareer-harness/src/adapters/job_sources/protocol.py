from typing import Protocol

from pydantic import BaseModel, ConfigDict

from src.shared.jobs import JobPosting, JobSearch, Quota
from src.shared.run_context import RunContext


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    postings: list[JobPosting]
    """The jobs found, in the source's order"""

    quota: Quota | None = None
    """Requests the source has left and allows, if it says"""


class SearchProtocol[Q: BaseModel](Protocol):
    query: type[Q]
    """The source's own search arguments"""

    async def search(
        self, query: Q, user_search: JobSearch | None, context: RunContext | None
    ) -> SearchResult:
        """Runs one search, with the user's own search over the agent's and the run's
        keys; raises SourceUnavailable when the source can't search"""
        ...
