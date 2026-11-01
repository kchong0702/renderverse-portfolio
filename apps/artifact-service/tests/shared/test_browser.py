import asyncio
from collections.abc import AsyncIterator

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from src.shared.browser import Browser


@pytest.fixture
async def browser() -> AsyncIterator[Browser]:
    shared = Browser(max_concurrent=4)
    yield shared
    await shared.close()


async def test_a_render_survives_chromium_dying(browser: Browser) -> None:
    calls = 0

    async def work(page: Page) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            browser_process = page.context.browser
            assert browser_process is not None
            await browser_process.close()
            await page.set_content("<p>never</p>")
        await page.set_content("<p>rendered</p>")
        return await page.inner_text("p")

    assert await browser.run(work) == "rendered"
    assert calls == 2


async def test_renders_beyond_the_limit_wait_their_turn() -> None:
    limited = Browser(max_concurrent=2)
    running = peak = 0

    async def work(page: Page) -> None:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.05)
        running -= 1

    try:
        await asyncio.gather(*(limited.run(work) for _ in range(6)))
    finally:
        await limited.close()

    assert peak == 2


async def test_errors_with_a_live_browser_are_not_retried(browser: Browser) -> None:
    calls = 0

    async def work(page: Page) -> None:
        nonlocal calls
        calls += 1
        await page.wait_for_selector("#missing", timeout=50)

    with pytest.raises(PlaywrightError):
        await browser.run(work)
    assert calls == 1


async def test_pages_cannot_reach_the_network(browser: Browser) -> None:
    async def work(page: Page) -> None:
        await page.goto("https://example.com")

    with pytest.raises(PlaywrightError, match="ERR_FAILED"):
        await browser.run(work)


async def test_page_scripts_do_not_run(browser: Browser) -> None:
    async def work(page: Page) -> str:
        await page.set_content("<script>document.title = 'ran'</script>")
        return await page.title()

    assert await browser.run(work) == ""
