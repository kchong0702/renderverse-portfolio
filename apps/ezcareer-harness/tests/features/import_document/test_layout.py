from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest
from fpdf import FPDF
from PIL import Image

from src.features.import_document.enums import Trait
from src.features.import_document.layout import suggest_look

TEMPLATES = Path(__file__).parents[5] / "packages/document-renderer/templates"


def _write(pdf: FPDF, x: float, *texts: str, top: float = 30) -> None:
    """Writes each text on a line of its own at x mm, from top down"""
    for number, text in enumerate(texts):
        pdf.set_xy(x, top + number * 8)
        pdf.cell(text=text)


def _resume(draw: Callable[[FPDF], None], font: str = "Helvetica") -> bytes:
    """A one-page résumé, its name and lines 70 mm in, written over what draw adds"""
    pdf = FPDF()
    pdf.add_page()
    draw(pdf)
    pdf.set_font(font, size=22)
    pdf.set_xy(70, 10)
    pdf.cell(text="Ada Lovelace")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font, size=11)
    _write(pdf, 70, "Experience", "Engineer, Acme", "Built the engine", "Skills")
    return bytes(pdf.output())


def _plain(pdf: FPDF) -> None:
    """Adds nothing"""


def _ruled_and_coloured(pdf: FPDF) -> None:
    """Rules under two headings and a blue name"""
    pdf.line(10, 37, 200, 37)
    pdf.line(10, 61, 200, 61)
    pdf.set_text_color(0, 79, 144)


def _two_columns(pdf: FPDF) -> None:
    """A right-hand column as long as the main one"""
    pdf.set_font("Helvetica", size=11)
    _write(pdf, 140, "Languages", "English", "French", "Python")


def _band(pdf: FPDF, left: bool) -> None:
    """A coloured band down the left or right with a column of its own"""
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(0 if left else 150, 0, 60, 297, style="F")
    pdf.set_font("Helvetica", size=11)
    _write(pdf, 5 if left else 155, "Contact", "ada@example.com", "London")


def _strips(pdf: FPDF) -> None:
    """Tinted strips behind two headings"""
    pdf.set_fill_color(230, 242, 240)
    pdf.rect(8, 27, 190, 6, style="F")
    pdf.rect(8, 51, 190, 6, style="F")


def _photo(pdf: FPDF, left: bool) -> None:
    """A photo at the top left or right"""
    pdf.image(Image.new("RGB", (90, 90), (120, 140, 160)), 10 if left else 170, 5, 30)


@pytest.mark.parametrize(
    ("draw", "font", "template", "columns", "traits"),
    [
        pytest.param(_plain, "Helvetica", "classic", 1, [], id="classic"),
        pytest.param(
            _ruled_and_coloured,
            "Helvetica",
            "classic",
            1,
            [Trait.RULED_HEADINGS, Trait.COLOURED_NAME],
            id="classic-ruled-coloured",
        ),
        pytest.param(_plain, "Times", "serif", 1, [Trait.SERIF_FONT], id="serif"),
        pytest.param(
            _strips, "Helvetica", "compact", 1, [Trait.TINTED_HEADINGS], id="compact"
        ),
        pytest.param(
            _two_columns, "Helvetica", "classic-two-column", 2, [], id="two-column"
        ),
        pytest.param(
            partial(_band, left=True),
            "Helvetica",
            "sidebar-band",
            2,
            [Trait.ACCENT_BAND],
            id="sidebar-band",
        ),
        pytest.param(
            partial(_band, left=False),
            "Helvetica",
            "sidebar-band-right",
            2,
            [Trait.ACCENT_BAND],
            id="sidebar-band-right",
        ),
        pytest.param(
            partial(_photo, left=False),
            "Helvetica",
            "photo-header",
            1,
            [Trait.PHOTO],
            id="photo-header",
        ),
        pytest.param(
            partial(_photo, left=True),
            "Helvetica",
            "photo-header-left",
            1,
            [Trait.PHOTO],
            id="photo-header-left",
        ),
    ],
)
def test_a_layout_suggests_the_template_closest_to_it(
    draw: Callable[[FPDF], None],
    font: str,
    template: str,
    columns: int,
    traits: list[Trait],
):
    suggestion = suggest_look(_resume(draw, font))

    assert (suggestion.template, suggestion.columns, suggestion.traits) == (
        template,
        columns,
        traits,
    )
    assert (TEMPLATES / f"{template}.yaml").is_file()


def test_suggestions_cover_every_template_document_renderer_has():
    assert {path.stem for path in TEMPLATES.glob("*.yaml")} == {
        "classic",
        "classic-two-column",
        "serif",
        "compact",
        "sidebar-band",
        "sidebar-band-right",
        "photo-header",
        "photo-header-left",
    }
