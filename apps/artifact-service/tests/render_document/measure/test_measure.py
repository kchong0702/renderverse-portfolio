import hashlib
import io
from collections.abc import AsyncIterator
from typing import Any

import pytest
from conftest import PNG, PNG_SHA
from document_schema import Document, MissingGlyph, RenderReport
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from src.features.render_document.html import render_html
from src.features.render_document.measure import measure
from src.shared.browser import Browser

LONG = "Designed and shipped the analytical engine's first published program " * 4


@pytest.fixture
async def browser() -> AsyncIterator[Browser]:
    shared = Browser(max_concurrent=4)
    yield shared
    await shared.close()


def _font_with(chars: str, name: str = "Partial") -> bytes:
    """A woff2 font named `name` inside the file, that can draw only `chars` and
    the space"""
    chars = "".join(dict.fromkeys(chars))
    names = [".notdef", "space", *(f"u{ord(c):04x}" for c in chars)]
    box = TTGlyphPen(None)
    box.moveTo((50, 0))
    box.lineTo((50, 700))
    box.lineTo((550, 700))
    box.lineTo((550, 0))
    box.closePath()
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({32: "space"} | {ord(c): f"u{ord(c):04x}" for c in chars})
    builder.setupGlyf(
        {
            name: TTGlyphPen(None).glyph() if name == "space" else box.glyph()
            for name in names
        }
    )
    builder.setupHorizontalMetrics({name: (600, 0) for name in names})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {"familyName": name, "styleName": "Regular", "psName": name.replace(" ", "")}
    )
    builder.setupOS2()
    builder.setupPost()
    builder.font.flavor = "woff2"
    out = io.BytesIO()
    builder.save(out)
    return out.getvalue()


async def _report(
    browser: Browser, data: dict[str, Any], extra_assets: dict[str, bytes] | None = None
) -> RenderReport:
    assets_data = {PNG_SHA: PNG, **(extra_assets or {})}
    rendered = render_html(Document.model_validate(data), assets_data)
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
    assert report.low_contrast == []
    assert report.missing_glyphs == []
    assert report.orphan_headings == []
    assert report.split_items == []
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


TITLE = "sections/exp/items/it_1/title"


@pytest.mark.parametrize(
    "css",
    [
        "h3 { color: #ccc }",
        "h3 { color: oklch(0.9 0 0) }",
        ".item { background: #222 } h3 { color: #333 }",
        "h3 { color: rgb(0 0 0 / 0.2) }",
        "h3 { color: #888; font-size: 12px }",
    ],
)
async def test_text_too_close_to_its_background_has_low_contrast(
    browser: Browser, document_data: dict[str, Any], css: str
) -> None:
    document_data["template"]["css"] += f" {css}"

    report = await _report(browser, document_data)

    ratios = {low.field: low.ratio for low in report.low_contrast}
    assert ratios[TITLE] < 4.5


async def test_measured_contrast_matches_wcag(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    # #ccc on white is 1.61:1 by the WCAG formula
    document_data["template"]["css"] += " h3 { color: #ccc }"

    report = await _report(browser, document_data)

    assert report.low_contrast[0].ratio == pytest.approx(1.61, abs=0.01)


@pytest.mark.parametrize(
    "css",
    [
        "h3 { color: #888; font-size: 24px }",
        "h3 { color: #888; font-size: 19px; font-weight: 700 }",
        ".item { background: linear-gradient(#fff, #fff) } h3 { color: #ccc }",
    ],
)
async def test_large_text_and_image_backgrounds_are_not_flagged(
    browser: Browser, document_data: dict[str, Any], css: str
) -> None:
    # #888 on white is 3.54:1, enough for large text but not for body text
    document_data["template"]["css"] += f" {css}"

    report = await _report(browser, document_data)

    assert report.low_contrast == []


@pytest.mark.parametrize(
    ("font_family", "name_in_file"),
    [
        ("Partial, serif", "Partial"),
        ('"Not Loaded", Partial, serif', "Partial"),
        ("Partial, serif", "Name In File"),
    ],
)
async def test_characters_the_document_font_lacks_are_missing_glyphs(
    browser: Browser, document_data: dict[str, Any], font_family: str, name_in_file: str
) -> None:
    font = _font_with("Programe", name_in_file)
    font_sha = hashlib.sha256(font).hexdigest()
    document_data["assets"][font_sha] = {"media_type": "font/woff2", "uri": "p.woff2"}
    document_data["presentation"] = {
        "fonts": [{"family": "Partial", "sha256": font_sha}]
    }
    document_data["template"]["css"] += f" h3 {{ font-family: {font_family} }}"
    document_data["content"]["sections"][1]["items"][0]["title"]["text"] = (
        "Programmer é ü"
    )

    report = await _report(browser, document_data, {font_sha: font})

    assert report.missing_glyphs == [
        MissingGlyph(field=TITLE, font="Partial", chars="éü")
    ]


async def test_missing_glyphs_name_the_first_font_when_a_second_one_fills_in(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    body = _font_with("Programe", "Body")
    symbols = _font_with("éü", "Symbols")
    shas = {hashlib.sha256(font).hexdigest(): font for font in (body, symbols)}
    for sha in shas:
        document_data["assets"][sha] = {"media_type": "font/woff2", "uri": "f.woff2"}
    document_data["presentation"] = {
        "fonts": [
            {"family": family, "sha256": sha}
            for family, sha in zip(["Body", "Symbols"], shas, strict=True)
        ]
    }
    document_data["template"]["css"] += " h3 { font-family: Body, Symbols, serif }"
    document_data["content"]["sections"][1]["items"][0]["title"]["text"] = (
        "Programmer é ü"
    )

    report = await _report(browser, document_data, shas)

    assert report.missing_glyphs == [MissingGlyph(field=TITLE, font="Body", chars="éü")]


async def test_a_generic_family_listed_before_a_document_font_is_the_font_checked(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    font = _font_with("Programe")
    font_sha = hashlib.sha256(font).hexdigest()
    document_data["assets"][font_sha] = {"media_type": "font/woff2", "uri": "p.woff2"}
    document_data["presentation"] = {
        "fonts": [{"family": "Partial", "sha256": font_sha}]
    }
    document_data["template"]["css"] += " h3 { font-family: sans-serif, Partial }"
    document_data["content"]["sections"][1]["items"][0]["title"]["text"] = (
        "Programmer \U0001f600"
    )

    report = await _report(browser, document_data, {font_sha: font})

    assert report.missing_glyphs == [
        MissingGlyph(field=TITLE, font="sans-serif", chars="\U0001f600")
    ]


async def test_an_item_running_over_a_page_break_is_split(
    browser: Browser, document_data: dict[str, Any]
) -> None:
    _bullets(document_data)[:] = [
        {"id": f"b_{n}", "text": {"text": LONG, "src": []}} for n in range(40)
    ]

    report = await _report(browser, document_data)

    assert report.pages >= 2
    assert report.split_items == ["sections/exp/items/it_1"]


@pytest.mark.parametrize(("pad_mm", "orphaned"), [(256, True), (200, False)])
async def test_a_heading_left_at_the_bottom_of_a_page_is_orphaned(
    browser: Browser, document_data: dict[str, Any], pad_mm: int, orphaned: bool
) -> None:
    # 265mm of usable height: a 256mm pad leaves room for the 20px heading but
    # not for the title after it
    document_data["template"]["html"] = (
        '<div class="pad"></div>{{#sections}}{{#is_experience}}'
        '<h2 data-field="{{heading.path}}">{{heading.text}}</h2>'
        '{{#items}}<h3 data-field="{{title.path}}">{{title.text}}</h3>{{/items}}'
        "{{/is_experience}}{{/sections}}"
    )
    document_data["template"]["css"] = (
        f".pad {{ height: {pad_mm}mm }} h2, h3 {{ margin: 0; font: 12px/20px sans-serif }}"
    )
    document_data["content"]["header"].pop("photo")
    document_data["assets"] = {}

    report = await _report(browser, document_data)

    assert report.orphan_headings == (["sections/exp/heading"] if orphaned else [])
