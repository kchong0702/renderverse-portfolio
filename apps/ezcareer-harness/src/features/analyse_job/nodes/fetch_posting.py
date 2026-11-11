import html_text
import httpx

from src.shared.jobs import PostingLine


async def fetch_posting(url: str) -> list[PostingLine]:
    """Fetch a posting page and split its visible text into numbered lines"""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(url)
    response.raise_for_status()
    texts = (
        line.strip() for line in html_text.extract_text(response.text).splitlines()
    )
    return [
        PostingLine(id=number, text=text)
        for number, text in enumerate(filter(None, texts), start=1)
    ]
