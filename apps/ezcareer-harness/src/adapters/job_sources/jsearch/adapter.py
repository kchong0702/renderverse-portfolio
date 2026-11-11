from circuitbreaker import CircuitBreaker

from src.adapters.job_sources.jsearch import client
from src.adapters.job_sources.jsearch.query import JSearchQuery
from src.adapters.job_sources.protocol import SearchResult
from src.core.config import get_settings
from src.shared.jobs import JobSearch, PostedWithin
from src.shared.run_context import RunContext


class JSearchAdapter:
    query = JSearchQuery
    """JSearch's own search arguments"""

    def __init__(self) -> None:
        """Reads the JSearch settings and closes its circuit"""
        self._settings = get_settings().jsearch
        """JSearch's URL, key and limits"""

        self._circuit = CircuitBreaker(
            failure_threshold=self._settings.failure_threshold,
            recovery_timeout=self._settings.recovery_seconds,
            expected_exception=lambda _, error: client.retryable(error),
            name="jsearch",
        )
        """Opens after failed pages in a row so later pages fail at once"""

    async def search(
        self,
        query: JSearchQuery,
        user_search: JobSearch | None,
        context: RunContext | None,
    ) -> SearchResult:
        """Searches Google for Jobs through JSearch, with the user's query, location
        and posting age over the agent's, on the run's key when it has one"""
        if user_search:
            text = user_search.query or query.query
            query = query.model_copy(
                update={
                    "query": f"{text} in {user_search.location}"
                    if user_search.location
                    else text,
                    "date_posted": {
                        PostedWithin.DAY: "today",
                        PostedWithin.WEEK: "week",
                        PostedWithin.MONTH: "month",
                    }[user_search.posted_within]
                    if user_search.posted_within
                    else query.date_posted,
                }
            )
        return await client.search(
            self._settings,
            self._circuit,
            query,
            (context and context.jsearch_api_key) or self._settings.api_key,
        )
