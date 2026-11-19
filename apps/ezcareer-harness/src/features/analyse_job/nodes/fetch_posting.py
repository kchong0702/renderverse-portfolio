import re
from urllib.parse import parse_qs, urlsplit

import html_text
import httpx

from src.shared.jobs import PostingLine

_LINKEDIN_VIEW = re.compile(r"/jobs/view/(?:[^/]*-)?(\d+)/?")


def _source(url: str) -> str:
    """LinkedIn's guest page of the posting a LinkedIn job link names, or else the
    url"""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return url
    view = _LINKEDIN_VIEW.fullmatch(parts.path)
    job_id = parse_qs(parts.query).get("currentJobId", [""])[0] or (
        view.group(1) if view else ""
    )
    return (
        f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        if job_id.isdigit()
        else url
    )


def posting_lines(text: str) -> list[PostingLine]:
    """The text's lines, stripped, without empty ones, numbered from one"""
    texts = (line.strip() for line in text.splitlines())
    return [
        PostingLine(id=number, text=text)
        for number, text in enumerate(filter(None, texts), start=1)
    ]


async def fetch_posting(url: str) -> list[PostingLine]:
    """Fetch a posting page, through LinkedIn's guest page for a LinkedIn job link,
    and split its visible text into numbered lines"""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(_source(url))
    response.raise_for_status()
    return posting_lines(html_text.extract_text(response.text))
