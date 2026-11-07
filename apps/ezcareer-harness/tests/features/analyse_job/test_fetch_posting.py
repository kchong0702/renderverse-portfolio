from pathlib import Path

import httpx
import pytest
import respx

from src.features.analyse_job.nodes import fetch_posting

URL = "https://jobs.example.com/acme/senior-backend"
POSTING = (Path(__file__).parent / "fixtures" / "posting.html").read_text()


@respx.mock
async def test_numbers_visible_lines_from_one():
    respx.get(URL).respond(200, html=POSTING)

    lines = await fetch_posting(URL)

    assert [(line.id, line.text) for line in lines[:4]] == [
        (1, "Senior Backend Engineer at Acme"),
        (2, "Home Jobs"),
        (3, "Senior Backend Engineer"),
        (4, "Acme builds payment tools for small shops."),
    ]
    assert lines[-1].id == len(lines)


@respx.mock
async def test_keeps_inline_formatting_on_one_line_and_drops_scripts():
    respx.get(URL).respond(200, html=POSTING)

    texts = [line.text for line in await fetch_posting(URL)]

    assert "5+ years of Python in production" in texts
    assert not any("dataLayer" in text or ".hero" in text for text in texts)
    assert all(text.strip() == text and text for text in texts)


@respx.mock
async def test_follows_redirects():
    respx.get("https://example.com/j/1").respond(301, headers={"Location": URL})
    respx.get(URL).respond(200, html=POSTING)

    lines = await fetch_posting("https://example.com/j/1")

    assert "Kubernetes" in [line.text for line in lines]


@respx.mock
async def test_raises_when_the_page_is_missing():
    respx.get(URL).respond(404)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_posting(URL)
