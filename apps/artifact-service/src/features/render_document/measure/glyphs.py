from collections.abc import Sequence
from pathlib import Path

from document_schema import MissingGlyph
from playwright.async_api import CDPSession, Page

from src.features.render_document.measure.schemas import MixedFontField

_PROBE_SCRIPT = Path(__file__).with_name("glyph_probe.js").read_text()

_LOADED_FAMILIES = (
    "[...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family)"
)
"""Families of the @font-face fonts the page loaded, the document's fonts"""

_GENERIC_FAMILIES = {
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "ui-serif",
    "ui-sans-serif",
    "ui-monospace",
    "ui-rounded",
    "math",
    "emoji",
    "fangsong",
}
"""CSS keywords for a font the browser chooses, not a named font. One is always
available, and is written without quotes, since a quoted keyword names a font
called that"""


async def _attributes(cdp: CDPSession, node_id: int) -> dict[str, str]:
    flat = (await cdp.send("DOM.getAttributes", {"nodeId": node_id}))["attributes"]
    return dict(zip(flat[::2], flat[1::2], strict=True))


async def _select(cdp: CDPSession, selector: str) -> list[int]:
    root = (await cdp.send("DOM.getDocument", {"depth": 0}))["root"]["nodeId"]
    query = {"nodeId": root, "selector": selector}
    return (await cdp.send("DOM.querySelectorAll", query))["nodeIds"]


async def _fonts(cdp: CDPSession, node_id: int) -> list[dict]:
    query = {"nodeId": node_id}
    return (await cdp.send("CSS.getPlatformFontsForNode", query))["fonts"]


def _css_font(font_family: str, loaded: set[str]) -> str:
    """The family in a font-family list that drew the text: the first one the
    page loaded or a generic keyword, or else the first one listed"""
    families = [family.strip().strip("\"'") for family in font_family.split(",")]
    available = loaded | _GENERIC_FAMILIES
    return next((f for f in families if f.lower() in available), families[0])


def _font_family_value(font: str) -> str:
    """A font-family value naming only `font`: a generic keyword as it is, any
    other name as a css string"""
    if font.lower() in _GENERIC_FAMILIES:
        return font
    escaped = font.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


async def find_mixed_font_fields(
    page: Page, cdp: CDPSession, value_paths: Sequence[str]
) -> list[MixedFontField]:
    """Fields whose text Chromium drew with more than one font, because the
    first font lacks some of the characters"""
    expected = set(value_paths)
    loaded = {family.lower() for family in await page.evaluate(_LOADED_FAMILIES)}
    mixed: dict[str, MixedFontField] = {}
    for node_id in await _select(cdp, "[data-field]"):
        field = (await _attributes(cdp, node_id)).get("data-field", "")
        if field not in expected or field in mixed:
            continue
        fonts = await _fonts(cdp, node_id)
        if len(fonts) < 2:
            continue
        style = await cdp.send("CSS.getComputedStyleForNode", {"nodeId": node_id})
        family = next(
            prop["value"]
            for prop in style["computedStyle"]
            if prop["name"] == "font-family"
        )
        mixed[field] = MixedFontField(field=field, font=_css_font(family, loaded))
    return list(mixed.values())


async def name_missing_glyphs(
    page: Page, cdp: CDPSession, mixed: Sequence[MixedFontField]
) -> list[MissingGlyph]:
    """Which characters of each field its font did not draw"""
    if not mixed:
        return []
    fields = [{"field": m.field, "family": _font_family_value(m.font)} for m in mixed]
    chars = await page.evaluate(_PROBE_SCRIPT, fields)
    drawn_by: dict[str, set[str]] = {}
    for node_id in await _select(cdp, "[data-glyph-probe]"):
        probe = (await _attributes(cdp, node_id))["data-glyph-probe"]
        drawn_by[probe] = {font["familyName"] for font in await _fonts(cdp, node_id)}
    missing = []
    for i, field in enumerate(mixed):
        # drawn by request font - drawn by system font ({inter,times,applesymbol} - {times,applesymbol} = {inter})
        # subtraction method to locate the requested font, none mean no diff hence cant locate the actual font
        # drawn_by only contains CDP's own font family name
        own = drawn_by[f"{i}:font"] - drawn_by[f"{i}:default"]
        if not own:
            continue
        lacking = [
            char
            for j, char in enumerate(chars[i])
            if drawn_by[f"{i}:{j}"]
            and not drawn_by[f"{i}:{j}"] & own  # i = field position, j = char position
        ]
        if lacking:
            missing.append(
                MissingGlyph(field=field.field, font=field.font, chars="".join(lacking))
            )
    return missing
