from pathlib import Path

import httpx
import pytest
import respx

from src.features.analyse_job.nodes import fetch_posting, posting_lines

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


GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4486649365"


@pytest.mark.parametrize(
    "link",
    [
        "https://www.linkedin.com/jobs/search-results/?currentJobId=4486649365&keywords=Senior%20Machine%20Learning%20Engineer&geoId=90010064",
        "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4486649365",
        "https://www.linkedin.com/jobs/view/4486649365/",
        "https://my.linkedin.com/jobs/view/senior-ai-engineer-at-avenga-4486649365",
    ],
)
@respx.mock
async def test_a_linkedin_job_link_is_read_from_linkedins_guest_page(link):
    respx.get(GUEST).respond(200, html=POSTING)

    lines = await fetch_posting(link)

    assert "Kubernetes" in [line.text for line in lines]


@respx.mock
async def test_a_linkedin_page_that_names_no_job_is_fetched_as_it_is():
    link = "https://www.linkedin.com/company/acme/jobs/"
    respx.get(link).respond(200, html=POSTING)

    lines = await fetch_posting(link)

    assert lines[0].text == "Senior Backend Engineer at Acme"


def test_pasted_text_becomes_numbered_lines_without_blank_ones():
    lines = posting_lines("  Senior AI Engineer \n\n Avenga\n   \nPython")

    assert [(line.id, line.text) for line in lines] == [
        (1, "Senior AI Engineer"),
        (2, "Avenga"),
        (3, "Python"),
    ]
