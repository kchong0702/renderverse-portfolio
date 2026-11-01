import base64
import hashlib
from typing import Any

import pytest
from conftest import PNG, PNG_SHA
from document_schema import DOCUMENT_ADAPTER

from src.features.render_document.exceptions import RenderError
from src.features.render_document.html import render_html

FONT = b"wOF2 not a real font"
FONT_SHA = hashlib.sha256(FONT).hexdigest()


def _render(data: dict[str, Any], assets_data: dict[str, bytes] | None = None):
    return render_html(
        DOCUMENT_ADAPTER.validate_python(data), assets_data or {PNG_SHA: PNG}
    )


def test_content_is_bound_into_the_template_and_escaped(
    document_data: dict[str, Any],
) -> None:
    bullets = document_data["content"]["sections"][1]["items"][0]["bullets"]
    bullets[0]["text"]["text"] = "<script>alert(1)</script>"

    html = _render(document_data).html

    assert '<h1 data-field="header/name">Ada Lovelace</h1>' in html
    assert (
        '<li data-field="sections/exp/items/it_1/bullets/b_1/text">'
        "&lt;script&gt;alert(1)&lt;/script&gt;</li>"
    ) in html
    assert "<script>" not in html


def test_page_rule_uses_the_page_size_and_each_margin_token(
    document_data: dict[str, Any],
) -> None:
    document_data["template"]["tokens"].update(
        {
            "--page-margin-top": "10mm",
            "--page-margin-right": "0.5in",
            "--page-margin-bottom": "20mm",
            "--page-margin-left": "12pt",
        }
    )
    document_data["presentation"] = {"page_size": "letter"}

    rendered = _render(document_data)

    assert "@page { size: letter; margin: 10mm 0.5in 20mm 12pt; }" in rendered.html
    assert rendered.margin_top_px == pytest.approx(10 * 96 / 25.4)
    assert rendered.margin_bottom_px == pytest.approx(20 * 96 / 25.4)
    assert rendered.content_width_px == pytest.approx(816 - 48 - 16)


def test_page_margins_can_be_zero(document_data: dict[str, Any]) -> None:
    for side in ("top", "right", "bottom", "left"):
        document_data["template"]["tokens"][f"--page-margin-{side}"] = "0"

    rendered = _render(document_data)

    assert "@page { size: A4; margin: 0 0 0 0; }" in rendered.html
    assert rendered.content_width_px == pytest.approx(210 * 96 / 25.4)


@pytest.mark.parametrize("margin", ["1em", "5%", "10mm 15mm"])
def test_page_margin_must_be_one_absolute_length(
    document_data: dict[str, Any], margin: str
) -> None:
    document_data["template"]["tokens"]["--page-margin-top"] = margin

    with pytest.raises(RenderError, match="must be one absolute length"):
        _render(document_data)


def test_token_overrides_replace_template_defaults(
    document_data: dict[str, Any],
) -> None:
    document_data["presentation"] = {"token_overrides": {"--accent": "#166534"}}

    html = _render(document_data).html

    assert "--accent: #166534;" in html
    assert "#1f3a5f" not in html


def test_fonts_and_images_are_inlined_as_data_uris(
    document_data: dict[str, Any],
) -> None:
    document_data["assets"][FONT_SHA] = {"media_type": "font/woff2", "uri": "f.woff2"}
    document_data["presentation"] = {
        "fonts": [{"family": "Source Sans 3", "weight": 600, "sha256": FONT_SHA}]
    }

    html = _render(document_data, {PNG_SHA: PNG, FONT_SHA: FONT}).html

    font_uri = f"data:font/woff2;base64,{base64.b64encode(FONT).decode()}"
    assert (
        f'@font-face {{ font-family: "Source Sans 3"; src: url({font_uri})'
        ' format("woff2"); font-weight: 600; font-style: normal; }'
    ) in html
    assert f'src="data:image/png;base64,{base64.b64encode(PNG).decode()}"' in html
    assert "asset:" not in html


@pytest.mark.parametrize(
    "tag",
    ["{{{header.name.text}}}", "{{& header.name.text}}", "{{> part}}", "{{=<% %>=}}"],
)
def test_unescaped_output_partials_and_delimiter_changes_are_rejected(
    document_data: dict[str, Any], tag: str
) -> None:
    document_data["template"]["html"] += tag

    with pytest.raises(RenderError, match="partials, delimiter changes or unescaped"):
        _render(document_data)


@pytest.mark.parametrize(
    "css",
    [
        "@page { margin: 0 }",
        "@PAGE { margin: 0 }",
        "@\\70 age { margin: 0 }",
        "@media print { @page { margin: 0 } }",
        "@supports (display: grid) { @media print { @page { margin: 0 } } }",
        "@import url(data:text/css,h1{color:red});",
        '@font-face { font-family: "X"; src: url(asset:x) }',
    ],
)
def test_template_css_cannot_set_page_rules_import_or_fonts(
    document_data: dict[str, Any], css: str
) -> None:
    document_data["template"]["css"] += css

    with pytest.raises(RenderError, match="template css may not use @"):
        _render(document_data)


@pytest.mark.parametrize(
    "css",
    [
        "h1 { --accent: red }",
        ":root{--x:1}",
        "@media print { :root { --x: 1 } }",
    ],
)
def test_template_css_cannot_declare_custom_properties(
    document_data: dict[str, Any], css: str
) -> None:
    document_data["template"]["css"] += css

    with pytest.raises(RenderError, match="may not declare --"):
        _render(document_data)


@pytest.mark.parametrize(
    "css",
    [
        "h1 { background: url(data:image/png;base64,AAAA) }",
        'h1 { background: url("https://example.com/a.png") }',
        'h1 { background: image-set("data:image/png;base64,AAAA" 1x) }',
        "h1 { background: image-set(url(a.png) 1x) }",
        "@media print { h1 { background: url(a.png) } }",
    ],
)
def test_template_css_urls_must_be_assets(
    document_data: dict[str, Any], css: str
) -> None:
    document_data["template"]["css"] += css

    with pytest.raises(RenderError, match="may only use url"):
        _render(document_data)


@pytest.mark.parametrize("end_tag", ["</style>", "</STYLE >", "</style/>"])
def test_template_css_cannot_close_the_style_element(
    document_data: dict[str, Any], end_tag: str
) -> None:
    document_data["template"]["css"] += f"{end_tag}<style>@page {{ margin: 0 }}"

    with pytest.raises(RenderError, match="may not contain </style>"):
        _render(document_data)


@pytest.mark.parametrize(
    "markup",
    [
        "<style>@page { margin: 0 }</style>",
        "<STYLE>h1 { color: red }</STYLE>",
        '<link rel="stylesheet" href="data:text/css,h1{}">',
    ],
)
def test_template_html_cannot_add_stylesheets(
    document_data: dict[str, Any], markup: str
) -> None:
    document_data["template"]["html"] += markup

    with pytest.raises(RenderError, match="may not add <style> or <link>"):
        _render(document_data)


def test_ordinary_rules_var_strings_and_asset_urls_are_allowed(
    document_data: dict[str, Any],
) -> None:
    document_data["template"]["css"] += (
        " @media print { h1 { color: var(--accent) } }"
        " .page-note::after { content: '@page url(a.png) --x: 1'; }"
        f" .logo {{ background: url(asset:{PNG_SHA}) }}"
        f' .mark {{ background: url("asset:{PNG_SHA}") }}'
    )

    html = _render(document_data).html

    assert "asset:" not in html


def test_broken_mustache_is_a_render_error(document_data: dict[str, Any]) -> None:
    document_data["template"]["html"] = "{{#sections}}<p>never closed</p>"

    with pytest.raises(RenderError, match="not valid Mustache"):
        _render(document_data)
