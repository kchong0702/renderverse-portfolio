from circuitbreaker import CircuitBreaker

from src.adapters.job_sources.jsearch.client import retryable, search
from src.adapters.job_sources.jsearch.query import JSearchQuery
from src.adapters.job_sources.protocol import SearchResult
from src.core.config import get_settings


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
            expected_exception=lambda _, error: retryable(error),
            name="jsearch",
        )
        """Opens after failed pages in a row so later pages fail at once"""

    async def search(self, query: JSearchQuery) -> SearchResult:
        """Searches Google for Jobs through JSearch"""
        return await search(self._settings, self._circuit, query)
