import io
import re
from collections.abc import Sequence
from urllib.parse import unquote

import pdfplumber

MARKER_HOST = "https://data-field.invalid/"
"""Address of the links mark.js adds, so they are told apart from the
template's own links. The .invalid domain can never resolve"""

_ITEM = re.compile(r"^(sections/[^/]+/items/[^/]+)/")
"""An item's path, taken from the path of a Value inside it"""

_HEADING = re.compile(r"^(sections/[^/]+)/heading$")
"""A section heading's path, with the section's path as the group"""


def pages_and_last_page_fill(
    pdf: bytes, margin_top_px: float, margin_bottom_px: float
) -> tuple[int, float]:
    """Page count, and how full the last page is between the top and bottom
    margins"""
    top_pt = margin_top_px * 72 / 96
    bottom_pt = margin_bottom_px * 72 / 96
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        last = document.pages[-1]
        bottoms = [obj["bottom"] for obj in (*last.chars, *last.images)]
        usable = last.height - top_pt - bottom_pt
        fill = (max(bottoms) - top_pt) / usable if bottoms else 0.0
        return len(document.pages), min(max(fill, 0.0), 1.0)


def field_pages(marked_pdf: bytes) -> dict[str, tuple[int, int]]:
    """First and last page each field is on, from the marker links"""
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    with pdfplumber.open(io.BytesIO(marked_pdf)) as document:
        for number, page in enumerate(document.pages, start=1):
            for link in page.hyperlinks:
                uri = link.get("uri") or ""
                if not uri.startswith(MARKER_HOST):
                    continue
                where, field = uri.removeprefix(MARKER_HOST).split("/", 1)
                field = unquote(field)
                if where == "start":
                    starts[field] = min(starts.get(field, number), number)
                else:
                    ends[field] = max(ends.get(field, number), number)
    return {field: (starts[field], ends.get(field, starts[field])) for field in starts}


def split_items(
    pages: dict[str, tuple[int, int]], value_paths: Sequence[str]
) -> list[str]:
    """Items whose fields start on one page and end on a later one"""
    spans: dict[str, list[tuple[int, int]]] = {}
    for path in value_paths:
        if (match := _ITEM.match(path)) and path in pages:
            spans.setdefault(match[1], []).append(pages[path])
    return [
        item
        for item, item_spans in spans.items()
        if min(start for start, _ in item_spans) < max(end for _, end in item_spans)
    ]


def orphan_headings(
    pages: dict[str, tuple[int, int]], value_paths: Sequence[str]
) -> list[str]:
    """Section headings that end on an earlier page than the section's first
    content, so they sit alone at the bottom of a page"""
    orphans = []
    for i, path in enumerate(value_paths):
        if not (match := _HEADING.match(path)) or path not in pages:
            continue
        section = f"{match[1]}/"
        following = next(
            (p for p in value_paths[i + 1 :] if p.startswith(section) and p in pages),
            None,
        )
        if following is not None and pages[path][1] < pages[following][0]:
            orphans.append(path)
    return orphans
