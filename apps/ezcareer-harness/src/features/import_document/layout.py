import io
from collections import Counter
from collections.abc import Mapping

import pdfplumber
from pdfplumber.page import Page

from src.features.import_document.enums import Trait
from src.features.import_document.schemas import LookSuggestion


def _filled(rect: Mapping[str, object]) -> bool:
    """Whether a pdfplumber rect is filled with something other than white"""
    return bool(rect["fill"]) and rect["non_stroking_color"] not in (
        None,
        (1,),
        (1, 1, 1),
        (0, 0, 0, 0),
    )


def _columns(page: Page) -> int:
    """2 when a gap splits the page's lines into two columns, else 1"""
    lines = page.objects.get("textlinehorizontal", [])
    for split in (
        line["x0"]
        for line in lines
        if page.width / 4 <= line["x0"] <= page.width * 3 / 4
    ):
        left = sum(line["x1"] <= split for line in lines)
        right = sum(line["x0"] >= split for line in lines)
        if (
            min(left, right) >= len(lines) / 5
            and len(lines) - left - right <= len(lines) / 7
        ):
            return 2
    return 1


def suggest_look(pdf: bytes) -> LookSuggestion:
    """The document-renderer template closest to the PDF's layout, and why"""
    with pdfplumber.open(io.BytesIO(pdf), laparams={"all_texts": True}) as document:
        first = document.pages[0]
        chars = [char for page in document.pages for char in page.chars]
        columns = max(_columns(page) for page in document.pages)
        band = next(
            (
                rect
                for rect in first.rects
                if _filled(rect)
                and rect["height"] >= first.height / 2
                and first.width * 0.15 <= rect["width"] <= first.width * 0.45
            ),
            None,
        )
        photo = next(
            (
                image
                for image in first.images
                if image["width"] >= 40 and image["height"] >= 40
            ),
            None,
        )
        tinted = (
            sum(
                _filled(rect)
                and 10 <= rect["height"] <= 30
                and rect["width"] >= page.width / 2
                for page in document.pages
                for rect in page.rects
            )
            >= 2
        )
        ruled = (
            sum(
                shape["height"] <= 2 and shape["width"] >= page.width * 0.3
                for page in document.pages
                for shape in page.lines + page.rects
            )
            >= 2
        )
        font = Counter(char["fontname"] for char in chars).most_common(1)[0][0].lower()
        serif = "sans" not in font and any(
            word in font
            for word in ("serif", "times", "garamond", "georgia", "cambria", "palatino")
        )
        name = max(chars, key=lambda char: char["size"])["non_stroking_color"]
        width = first.width
    return LookSuggestion(
        template=(
            (
                "sidebar-band"
                if band["x0"] + band["x1"] < width
                else "sidebar-band-right"
            )
            if band
            else (
                "photo-header-left"
                if photo["x0"] + photo["x1"] < width
                else "photo-header"
            )
            if photo
            else "classic-two-column"
            if columns == 2
            else "compact"
            if tinted
            else "serif"
            if serif
            else "classic"
        ),
        columns=columns,
        traits=[
            trait
            for trait, present in (
                (Trait.ACCENT_BAND, band is not None),
                (Trait.PHOTO, photo is not None),
                (Trait.TINTED_HEADINGS, tinted),
                (Trait.RULED_HEADINGS, ruled),
                (Trait.SERIF_FONT, serif),
                (
                    Trait.COLOURED_NAME,
                    isinstance(name, tuple)
                    and len(name) in (3, 4)
                    and max(name[:3]) - min(name[:3]) > 0.15,
                ),
            )
            if present
        ],
    )
