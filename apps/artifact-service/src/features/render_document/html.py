import base64
import re
from collections.abc import Mapping

import chevron
from document_schema import ASSET_REF, Document, PageSize

from src.features.render_document.exceptions import RenderError
from src.features.render_document.policy import (
    check_rendered_body,
    check_template_css,
    check_template_html,
)
from src.features.render_document.schemas import RenderedHtml
from src.features.render_document.view import build_view

_PX_PER_UNIT = {
    "px": 1.0,
    "pt": 96 / 72,
    "pc": 16.0,
    "mm": 96 / 25.4,
    "cm": 96 / 2.54,
    "in": 96.0,
}

_PAGE = {
    PageSize.A4: ("A4", 210 * _PX_PER_UNIT["mm"]),
    PageSize.LETTER: ("letter", 8.5 * _PX_PER_UNIT["in"]),
}

_LENGTH = re.compile(r"^(?:0|(\d+(?:\.\d+)?)(px|pt|pc|mm|cm|in))$")
"""One absolute CSS length, such as 16mm or 0.5in, or a bare 0

Used for the --page-margin-<side> tokens, which the renderer converts to pixels
itself because Chromium does not resolve var() inside @page. Relative units like
em or % and multi-value lengths are rejected
"""

_MARGIN_SIDES = ("top", "right", "bottom", "left")
"""Order of the four values in the @page margin shorthand"""


def _length_px(token: str, value: str) -> float:
    """Convert supported css unit to px"""
    match = _LENGTH.match(value)
    if match is None:
        raise RenderError(f"{token} {value!r} must be one absolute length")
    number, unit = match.groups()
    return float(number) * _PX_PER_UNIT[unit] if unit else 0.0


def _data_uri(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode()}"


def _asset_uri(sha: str, document: Document, assets_data: Mapping[str, bytes]) -> str:
    asset = document.assets.get(sha)
    if asset is None:
        raise RenderError(f"asset:{sha} names no document asset")
    return _data_uri(asset.media_type, assets_data[sha])


def render_html(document: Document, assets_data: Mapping[str, bytes]) -> RenderedHtml:
    template = document.template
    presentation = document.presentation

    check_template_html(template.html)
    check_template_css(template.css)

    view = build_view(document.content, set(presentation.hidden))
    try:
        body = chevron.render(template.html, view.content.model_dump(mode="json"))
    except chevron.ChevronError as exc:
        raise RenderError(f"template is not valid Mustache: {exc}") from exc

    check_rendered_body(body)

    tokens = {**template.tokens, **presentation.token_overrides}
    margins = {side: tokens.get(f"--page-margin-{side}", "0") for side in _MARGIN_SIDES}
    margins_px = {
        side: _length_px(f"--page-margin-{side}", value)
        for side, value in margins.items()
    }
    page_name, page_width_px = _PAGE[presentation.page_size]
    fonts = [
        f'@font-face {{ font-family: "{font.family}";'
        f" src: url({_data_uri('font/woff2', assets_data[font.sha256])})"
        ' format("woff2");'
        f" font-weight: {font.weight}; font-style: {font.style}; }}"
        for font in presentation.fonts
    ]
    root = " ".join(f"{name}: {value};" for name, value in tokens.items())
    css = "\n".join(
        [
            f"@page {{ size: {page_name}; margin: {' '.join(margins.values())}; }}",
            *fonts,
            f":root {{ {root} }}",
            "body { margin: 0; }",
            template.css,
        ]
    )
    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>{css}</style></head><body>{body}</body></html>"
    )

    return RenderedHtml(
        html=ASSET_REF.sub(
            lambda match: _asset_uri(match.group(1), document, assets_data), html
        ),
        value_paths=view.value_paths,
        content_width_px=page_width_px - margins_px["left"] - margins_px["right"],
        margin_top_px=margins_px["top"],
        margin_bottom_px=margins_px["bottom"],
    )
