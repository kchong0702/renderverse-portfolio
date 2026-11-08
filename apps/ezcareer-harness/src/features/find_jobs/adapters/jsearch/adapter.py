from src.core.config import get_settings
from src.features.find_jobs.adapters.base import SearchResult
from src.features.find_jobs.adapters.jsearch.client import search
from src.features.find_jobs.adapters.jsearch.query import JSearchQuery
from src.shared.adapters import Adapter


async def _search(query: JSearchQuery) -> SearchResult:
    """Searches JSearch with the app's current settings"""
    return await search(get_settings().jsearch, query)


JSEARCH = Adapter[SearchResult](
    name="jsearch",
    query=JSearchQuery,
    usage=(
        "JSearch allows 200 requests a month and every 10 jobs costs one; each "
        "result says how many are left."
    ),
    run=_search,
)
"""Job postings from Google for Jobs through JSearch on RapidAPI"""
