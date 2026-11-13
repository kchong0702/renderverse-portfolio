import httpx2
import pytest

from src.adapters.job_sources.jsearch import JSearchClient, JSearchQuery
from src.core.config import JSearchSettings
from src.core.exceptions import ServiceUnavailable


def _client(*pages: httpx2.Response) -> tuple[JSearchClient, list[httpx2.Request]]:
    """A client whose JSearch answers each request with the next page"""
    sent: list[httpx2.Request] = []
    answers = iter(pages)

    def answer(request: httpx2.Request) -> httpx2.Response:
        """The next page, keeping the request"""
        sent.append(request)
        return next(answers)

    return (
        JSearchClient(
            JSearchSettings(retry_max_wait_seconds=0), httpx2.MockTransport(answer)
        ),
        sent,
    )


def _page(count: int, cursor: str | None, start: int = 0) -> httpx2.Response:
    """A page of count jobs numbered from start, ending with cursor"""
    return httpx2.Response(
        200,
        json={
            "data": {
                "jobs": [
                    {
                        "job_id": f"job-{n}",
                        "job_title": "Backend Engineer",
                        "employer_name": "Acme",
                        "job_apply_link": f"https://jobs.example.com/{n}",
                    }
                    for n in range(start, start + count)
                ],
                "cursor": cursor,
            }
        },
    )


async def test_sends_the_key_and_every_search_option():
    client, sent = _client(_page(1, None))

    await client.search(
        "rapidapi-key",
        JSearchQuery(
            query="platform engineer",
            country="GB",
            work_from_home=True,
            date_posted="month",
            employment_types=["FULLTIME", "CONTRACTOR"],
            job_requirements=["no_degree"],
            radius_km=25,
        ),
    )

    [request] = sent
    assert request.headers["X-RapidAPI-Key"] == "rapidapi-key"
    assert request.headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"
    assert dict(request.url.params) == {
        "query": "platform engineer",
        "country": "gb",
        "work_from_home": "true",
        "date_posted": "month",
        "employment_types": "FULLTIME,CONTRACTOR",
        "job_requirements": "no_degree",
        "radius": "25",
    }


async def test_follows_the_cursor_until_it_has_max_jobs():
    client, sent = _client(_page(10, "2"), _page(10, "3", 10), _page(15, "4", 20))

    found = await client.search("key", JSearchQuery(query="backend engineer"))

    assert [request.url.params.get("cursor") for request in sent] == [None, "2", "3"]
    assert [job.job_id for job in found.jobs] == [f"job-{n}" for n in range(30)]


async def test_stops_when_jsearch_has_no_more_pages():
    client, sent = _client(_page(4, None))

    found = await client.search("key", JSearchQuery(query="backend engineer"))

    assert (len(sent), len(found.jobs)) == (1, 4)


async def test_reads_the_quota_from_the_rate_limit_headers():
    page = _page(1, None)
    page.headers["x-ratelimit-requests-remaining"] = "42"
    page.headers["x-ratelimit-requests-limit"] = "200"
    client, _ = _client(page)

    found = await client.search("key", JSearchQuery(query="backend engineer"))

    assert (found.remaining, found.limit) == (42, 200)


async def test_has_no_quota_when_jsearch_sends_no_rate_limit_headers():
    client, _ = _client(_page(1, None))

    found = await client.search("key", JSearchQuery(query="backend engineer"))

    assert (found.remaining, found.limit) == (None, None)


async def test_retries_a_rate_limited_page():
    client, sent = _client(httpx2.Response(429), _page(3, None))

    found = await client.search("key", JSearchQuery(query="backend engineer"))

    assert (len(sent), len(found.jobs)) == (2, 3)


async def test_jsearch_still_failing_after_its_tries_names_its_status():
    client, sent = _client(*[httpx2.Response(503)] * 3)

    with pytest.raises(ServiceUnavailable, match="^JSearch answered 503$"):
        await client.search("key", JSearchQuery(query="backend engineer"))

    assert len(sent) == 3


async def test_a_refused_key_is_not_tried_again():
    client, sent = _client(httpx2.Response(403))

    with pytest.raises(ServiceUnavailable, match="^JSearch answered 403$"):
        await client.search("key", JSearchQuery(query="backend engineer"))

    assert len(sent) == 1
