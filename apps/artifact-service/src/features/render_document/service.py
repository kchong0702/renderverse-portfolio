import asyncio
from hashlib import sha256
from typing import Any

from document_schema import Report
from playwright.async_api import Page, Route

from src.core.config import get_settings
from src.features.render_document.browser import Browser
from src.features.render_document.schemas import RenderRequest, RenderResponse

_ORIGIN = "http://renderer/"

_settings = get_settings()


async def render_document(request: RenderRequest, browser: Browser) -> RenderResponse:
    """Prints the document as a PDF and measures its pages"""
    dist = _settings.renderer.dist.resolve()

    async def serve(route: Route) -> None:
        """Answers with an asset's bytes or a renderer file, and fails the rest"""
        path = route.request.url.removeprefix(_ORIGIN).split("?")[0]
        file = (dist / path).resolve()
        asset = path.removeprefix("assets/")
        if asset in request.assets:
            await route.fulfill(
                body=request.assets[asset],
                content_type=request.document.assets[asset].media_type,
            )
        elif file.is_relative_to(dist) and file.is_file():
            await route.fulfill(path=file)
        else:
            await route.abort()

    async def work(page: Page) -> tuple[Any, bytes]:
        """Loads the renderer on page, lays the document out and prints it"""
        async with asyncio.timeout(_settings.renderer.timeout_s):
            await page.route(f"{_ORIGIN}**", serve)
            await page.goto(f"{_ORIGIN}index.html")
            measurement = await page.evaluate(
                "input => window.render(input)",
                {
                    "document": request.document.model_dump(mode="json"),
                    "template": request.template.model_dump(mode="json"),
                },
            )
            pdf = await page.pdf(prefer_css_page_size=True, print_background=True)
            return measurement, pdf

    measurement, pdf = await browser.run(work)
    report = Report.model_validate(
        {**measurement, "render_id": sha256(pdf).hexdigest()}
    )
    return RenderResponse(pdf=pdf, report=report)
