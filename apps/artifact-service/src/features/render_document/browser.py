import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, Playwright, async_playwright


class Browser:
    def __init__(self, max_concurrent: int) -> None:
        """A Chromium shared by renders, started on first use"""
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(max_concurrent)

    async def _ensure_browser(self) -> PlaywrightBrowser:
        """The running Chromium, launched again if it has gone"""
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    chromium_sandbox=True
                )
            return self._browser

    async def _run_on[T](
        self, browser: PlaywrightBrowser, work: Callable[[Page], Awaitable[T]]
    ) -> T:
        """Runs work on a fresh page whose requests fail unless work routes them"""
        context = await browser.new_context(service_workers="block")
        try:
            await context.route("**/*", lambda route: route.abort())
            return await work(await context.new_page())
        finally:
            with suppress(PlaywrightError):
                await context.close()

    async def run[T](self, work: Callable[[Page], Awaitable[T]]) -> T:
        """Runs work on a fresh page, waiting for a free slot"""
        async with self._slots:
            browser = await self._ensure_browser()
            try:
                return await self._run_on(browser, work)
            except PlaywrightError:
                if browser.is_connected():
                    raise
                return await self._run_on(await self._ensure_browser(), work)

    async def close(self) -> None:
        """Stops Chromium"""
        async with self._lock:
            if self._browser is not None:
                with suppress(PlaywrightError):
                    await self._browser.close()
            if self._playwright is not None:
                await self._playwright.stop()
            self._browser = None
            self._playwright = None
