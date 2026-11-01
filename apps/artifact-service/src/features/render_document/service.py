from src.features.render_document.html import render_html
from src.features.render_document.measure import measure
from src.features.render_document.schemas import RenderRequest, RenderResponse
from src.shared.browser import Browser


async def render_document(request: RenderRequest, browser: Browser) -> RenderResponse:
    rendered = render_html(request.document, request.assets_data)
    measured = await measure(browser, rendered)
    return RenderResponse(html=rendered.html, pdf=measured.pdf, report=measured.report)
