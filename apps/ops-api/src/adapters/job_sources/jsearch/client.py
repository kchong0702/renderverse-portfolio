from __future__ import annotations

from urllib.parse import urlsplit

import httpx2
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.adapters.job_sources.jsearch.schemas import (
    JSearchQuery,
    JSearchResponse,
    JSearchResults,
)
from src.core.config import JSearchSettings
from src.core.exceptions import InvalidInput, ServiceUnavailable
from src.core.logging import get_logger

logger = get_logger(__name__)


def _retryable(error: BaseException) -> bool:
    """Whether JSearch rate-limited a page, was down or never answered"""
    if isinstance(error, httpx2.HTTPStatusError):
        return error.response.status_code in {429, 500, 502, 503}
    return isinstance(error, httpx2.TransportError)


def _header(response: httpx2.Response, name: str) -> int | None:
    """A rate-limit header's number; None when JSearch did not send it"""
    value = response.headers.get(name)
    return int(value) if value else None


class JSearchClient:
    def __init__(
        self,
        settings: JSearchSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime, sending through transport when given"""
        self._settings = settings
        """JSearch's URL, timeout and retries"""

        self._http = httpx2.AsyncClient(
            timeout=settings.timeout_seconds, transport=transport
        )
        """The HTTP client every search goes through"""

    async def _page(
        self, api_key: str, params: dict[str, str | int | bool]
    ) -> httpx2.Response:
        """One page of results, tried again with backoff while retryable"""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_retryable),
            stop=stop_after_attempt(self._settings.retry_attempts),
            wait=wait_exponential(max=self._settings.retry_max_wait_seconds),
            reraise=True,
        ):
            with attempt:
                response = await self._http.get(
                    self._settings.url,
                    params=params,
                    headers={
                        "X-RapidAPI-Key": api_key,
                        "X-RapidAPI-Host": urlsplit(self._settings.url).hostname or "",
                    },
                )
                response.raise_for_status()
        return response

    async def search(self, api_key: str, query: JSearchQuery) -> JSearchResults:
        """Up to query.max_jobs results on the user's key, following JSearch's cursor
        until it has enough or runs out; InvalidInput when JSearch refuses the key,
        ServiceUnavailable when it fails"""
        params: dict[str, str | int | bool] = {
            "query": query.query,
            "date_posted": query.date_posted,
            "work_from_home": query.work_from_home,
        }
        if query.country:
            params["country"] = query.country.lower()
        if query.employment_types:
            params["employment_types"] = ",".join(query.employment_types)
        if query.job_requirements:
            params["job_requirements"] = ",".join(query.job_requirements)
        if query.radius_km:
            params["radius"] = query.radius_km
        jobs = []
        cursor = None
        try:
            while len(jobs) < query.max_jobs:
                response = await self._page(
                    api_key, params | ({"cursor": cursor} if cursor else {})
                )
                page = JSearchResponse.model_validate_json(response.content).data
                jobs += page.jobs
                cursor = page.cursor
                if not cursor or not page.jobs:
                    break
        except httpx2.HTTPStatusError as error:
            logger.warning("jsearch_error", status_code=error.response.status_code)
            if error.response.status_code in {401, 403}:
                raise InvalidInput("JSearch refused the key") from error
            raise ServiceUnavailable(
                f"JSearch answered {error.response.status_code}"
            ) from error
        except httpx2.HTTPError as error:
            raise ServiceUnavailable(
                "JSearch could not be reached; try again later"
            ) from error
        except ValidationError as error:
            raise ServiceUnavailable(
                "JSearch sent a response Ops cannot read"
            ) from error
        return JSearchResults(
            jobs=jobs[: query.max_jobs],
            remaining=_header(response, "x-ratelimit-requests-remaining"),
            limit=_header(response, "x-ratelimit-requests-limit"),
        )

    async def aclose(self) -> None:
        """Close the HTTP client"""
        await self._http.aclose()


__all__ = ["JSearchClient"]
