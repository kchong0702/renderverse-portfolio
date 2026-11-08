from src.core.config import get_settings
from src.features.find_jobs.adapters.base import JobAdapter, SearchResult
from src.features.find_jobs.adapters.jsearch.client import search
from src.features.find_jobs.adapters.jsearch.query import JSearchQuery


async def _search(query: JSearchQuery) -> SearchResult:
    """Searches JSearch with the app's current settings"""
    return await search(get_settings().jsearch, query)


JSEARCH = JobAdapter(
    name="jsearch",
    query=JSearchQuery,
    usage=(
        "JSearch allows 200 requests a month and every 10 jobs costs one; each "
        "result says how many are left."
    ),
    search=_search,
)
"""Job postings from Google for Jobs through JSearch on RapidAPI"""
