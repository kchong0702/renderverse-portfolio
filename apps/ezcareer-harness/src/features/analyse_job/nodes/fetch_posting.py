import re
from urllib.parse import parse_qs, urlsplit

import html_text
import httpx

from src.shared.jobs import PostingLine, posting_lines


async def fetch_posting(url: str) -> list[PostingLine]:
    """Fetch a posting page, through LinkedIn's guest page for a LinkedIn job link,
    and split its visible text into numbered lines"""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        view = re.fullmatch(r"/jobs/view/(?:[^/]*-)?(\d+)/?", parts.path)
        job_id = parse_qs(parts.query).get("currentJobId", [""])[0] or (
            view.group(1) if view else ""
        )
        if job_id.isdigit():
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(url)
    response.raise_for_status()
    return posting_lines(html_text.extract_text(response.text))
