import io
import math
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import pdfplumber
from document_schema import RenderReport
from playwright.async_api import Page

from src.features.render_document.schemas import Measurement, RenderedHtml
from src.shared.browser import Browser

_SCRIPT = Path(__file__).with_name("measure.js").read_text()


def _paginate(
    pdf: bytes, margin_top_px: float, margin_bottom_px: float
) -> tuple[int, float]:
    top_pt = margin_top_px * 72 / 96
    bottom_pt = margin_bottom_px * 72 / 96
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        last = document.pages[-1]
        bottoms = [obj["bottom"] for obj in (*last.chars, *last.images)]
        usable = last.height - top_pt - bottom_pt
        fill = (max(bottoms) - top_pt) / usable if bottoms else 0.0
        return len(document.pages), min(max(fill, 0.0), 1.0)


async def _measure_page(
    page: Page, html: str, value_paths: Sequence[str], content_width_px: float
) -> tuple[dict[str, Any], bytes]:
    await page.set_viewport_size(
        {"width": math.floor(content_width_px), "height": 1000}
    )
    await page.emulate_media(media="print")
    await page.set_content(html, wait_until="load")
    await page.evaluate("document.fonts.ready.then(() => true)")
    found = await page.evaluate(_SCRIPT, list(value_paths))
    pdf = await page.pdf(prefer_css_page_size=True, print_background=True)
    return found, pdf


async def measure(browser: Browser, rendered: RenderedHtml) -> Measurement:
    found, pdf = await browser.run(
        lambda page: _measure_page(
            page, rendered.html, rendered.value_paths, rendered.content_width_px
        )
    )
    pages, fill = _paginate(pdf, rendered.margin_top_px, rendered.margin_bottom_px)
    bound = set(found["bound"])
    return Measurement(
        pdf=pdf,
        report=RenderReport(
            render_id=sha256(rendered.html.encode()).hexdigest(),
            pages=pages,
            last_page_fill=fill,
            overflow=found["overflow"],
            line_counts=found["lines"],
            empty_fields=found["empty"],
            unbound_fields=[p for p in rendered.value_paths if p not in bound],
        ),
    )
