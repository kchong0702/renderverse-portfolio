from collections.abc import AsyncIterator
from typing import Any

import pytest
from conftest import PNG, PNG_SHA
from document_schema import Document, RenderReport

from src.features.render_document.html import render_html
from src.features.render_document.measure import measure
from src.shared.browser import Browser

LONG = "Designed and shipped the analytical engine's first published program " * 4


@pytest.fixture
async def browser() -> AsyncIterator[Browser]:
    shared = Browser(max_concurrent=4)
    yield shared
    await shared.close()


async def _report(browser: Browser, data: dict[str, Any]) -> RenderReport:
    rendered = render_html(Document.model_validate(data), {PNG_SHA: PNG})
    measured = await measure(browser, rendered)
    assert measured.pdf.startswith(b"%PDF")
    return measured.report


def _bullets(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data["content"]["sections"][1]["items"][0]["bullets"]


async def test_a_template_that_shows_everything_reports_no_problems(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    report = await _report(browser, document_data)

    assert report.pages == 1
    assert 0 < report.last_page_fill < 0.5
    assert report.unbound_fields == []
    assert report.empty_fields == []
    assert report.overflow == []
    assert report.line_counts["header/name"] == 1


async def test_values_the_template_never_prints_are_unbound(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    html = document_data["template"]["html"]
    document_data["template"]["html"] = html.replace(
        '{{#links}}<a href="{{url.text}}" data-field="{{url.path}}">'
        "{{url.text}}</a>{{/links}}",
        "",
    )

    report = await _report(browser, document_data)

    assert report.unbound_fields == ["sections/exp/items/it_1/links/l_1/url"]


async def test_values_hidden_by_css_are_unbound(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    document_data["template"]["css"] += " li { display: none; }"

    report = await _report(browser, document_data)

    assert report.unbound_fields == [
        "sections/exp/items/it_1/bullets/b_1/text",
        "sections/exp/items/it_1/bullets/b_2/text",
    ]


async def test_a_bound_value_with_no_text_is_empty(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    _bullets(document_data)[1]["text"]["text"] = " "

    report = await _report(browser, document_data)

    assert report.empty_fields == ["sections/exp/items/it_1/bullets/b_2/text"]
    assert report.unbound_fields == []


async def test_text_wider_than_its_box_overflows(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    document_data["template"]["css"] += (
        " h3 { width: 40px; white-space: nowrap; overflow: hidden; }"
    )

    report = await _report(browser, document_data)

    [overflow] = report.overflow
    assert overflow.field == "sections/exp/items/it_1/title"
    assert overflow.available_px == 40
    assert overflow.needed_px > 40


async def test_long_values_wrap_onto_more_lines(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    _bullets(document_data)[0]["text"]["text"] = LONG

    report = await _report(browser, document_data)

    assert report.line_counts["sections/exp/items/it_1/bullets/b_1/text"] > 2
    assert report.line_counts["sections/exp/items/it_1/bullets/b_2/text"] == 1


async def test_wider_margins_leave_less_room_per_line(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    _bullets(document_data)[0]["text"]["text"] = LONG
    path = "sections/exp/items/it_1/bullets/b_1/text"
    narrow = await _report(browser, document_data)
    document_data["template"]["tokens"]["--page-margin-left"] = "50mm"
    document_data["template"]["tokens"]["--page-margin-right"] = "50mm"

    wide = await _report(browser, document_data)

    assert wide.line_counts[path] > narrow.line_counts[path]


@pytest.mark.parametrize(("top", "bottom"), [(16, 16), (10, 60), (60, 10)])
async def test_fill_is_measured_inside_the_top_and_bottom_margins(
    browser: Browser, document_data: dict[str, Any], top: int, bottom: int
) -> None:
    usable_mm = 297 - top - bottom
    tokens = document_data["template"]["tokens"]
    tokens["--page-margin-top"] = f"{top}mm"
    tokens["--page-margin-bottom"] = f"{bottom}mm"
    # Text whose last line ends halfway down the usable height
    document_data["template"]["html"] = (
        '<div class="half"><span data-field="{{header.name.path}}">'
        "{{header.name.text}}</span></div>"
    )
    document_data["template"]["css"] = (
        f".half {{ height: {usable_mm / 2}mm; display: flex; align-items: flex-end;"
        " font: 12px/1 sans-serif; }"
    )
    document_data["content"]["header"].pop("photo")
    document_data["assets"] = {}

    report = await _report(browser, document_data)

    assert report.pages == 1
    assert report.last_page_fill == pytest.approx(0.5, abs=0.01)


async def test_content_past_one_page_is_paginated(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    _bullets(document_data)[:] = [
        {"id": f"b_{n}", "text": {"text": LONG, "src": []}} for n in range(40)
    ]

    report = await _report(browser, document_data)

    assert report.pages >= 2
    assert 0 < report.last_page_fill <= 1


async def test_the_render_id_identifies_the_html(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    first = await _report(browser, document_data)
    again = await _report(browser, document_data)
    _bullets(document_data)[0]["text"]["text"] = "Changed"
    changed = await _report(browser, document_data)

    assert first.render_id == again.render_id
    assert first.render_id != changed.render_id
