import math
from hashlib import sha256
from pathlib import Path

from document_schema import RenderReport
from playwright.async_api import Page

from src.features.render_document.measure.glyphs import (
    find_mixed_font_fields,
    name_missing_glyphs,
)
from src.features.render_document.measure.pdf import (
    MARKER_HOST,
    field_pages,
    orphan_headings,
    pages_and_last_page_fill,
    split_items,
)
from src.features.render_document.measure.schemas import DomFindings, PageFindings
from src.features.render_document.schemas import Measurement, RenderedHtml
from src.shared.browser import Browser

_MEASURE_SCRIPT = Path(__file__).with_name("dom.js").read_text()
_MARK_SCRIPT = Path(__file__).with_name("mark.js").read_text()


async def _measure_page(page: Page, rendered: RenderedHtml) -> PageFindings:
    await page.set_viewport_size(
        {"width": math.floor(rendered.content_width_px), "height": 1000}
    )
    await page.emulate_media(media="print")
    await page.set_content(rendered.html, wait_until="load")
    await page.evaluate("document.fonts.ready.then(() => true)")
    found = await page.evaluate(_MEASURE_SCRIPT, list(rendered.value_paths))
    pdf = await page.pdf(prefer_css_page_size=True, print_background=True)

    cdp = await page.context.new_cdp_session(page)
    await cdp.send("DOM.enable")
    await cdp.send("CSS.enable")
    mixed = await find_mixed_font_fields(page, cdp, rendered.value_paths)

    await page.evaluate(_MARK_SCRIPT, MARKER_HOST)
    marked_pdf = await page.pdf(prefer_css_page_size=True, print_background=True)
    missing_glyphs = await name_missing_glyphs(page, cdp, mixed)

    return PageFindings(
        dom=DomFindings.model_validate(found),
        pdf=pdf,
        marked_pdf=marked_pdf,
        missing_glyphs=missing_glyphs,
    )


async def measure(browser: Browser, rendered: RenderedHtml) -> Measurement:
    findings = await browser.run(lambda page: _measure_page(page, rendered))
    pages, fill = pages_and_last_page_fill(
        findings.pdf, rendered.margin_top_px, rendered.margin_bottom_px
    )
    spans = field_pages(findings.marked_pdf)
    bound = set(findings.dom.bound)
    return Measurement(
        pdf=findings.pdf,
        report=RenderReport(
            render_id=sha256(rendered.html.encode()).hexdigest(),
            pages=pages,
            last_page_fill=fill,
            overflow=findings.dom.overflow,
            low_contrast=findings.dom.low_contrast,
            missing_glyphs=findings.missing_glyphs,
            line_counts=findings.dom.lines,
            empty_fields=findings.dom.empty,
            unbound_fields=[p for p in rendered.value_paths if p not in bound],
            orphan_headings=orphan_headings(spans, rendered.value_paths),
            split_items=split_items(spans, rendered.value_paths),
        ),
    )
