from src.core.config import get_settings
from src.features.find_jobs.adapters.jsearch.client import search
from src.features.find_jobs.adapters.jsearch.query import JSearchQuery
from src.features.find_jobs.adapters.protocol import SearchResult


class JSearchAdapter:
    query = JSearchQuery
    """JSearch's own search arguments"""

    usage = (
        "JSearch allows 200 requests a month and every 10 jobs costs one; each "
        "result says how many are left."
    )
    """What a JSearch search costs"""

    async def search(self, query: JSearchQuery) -> SearchResult:
        """Searches Google for Jobs through JSearch with the app's current settings"""
        return await search(get_settings().jsearch, query)
