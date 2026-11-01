from __future__ import annotations

from typing import Any

import pytest
from conftest import RENDER_ID
from pydantic import ValidationError

from document_schema import RenderReport


@pytest.fixture
def report() -> dict[str, Any]:
    return {
        "render_id": RENDER_ID,
        "pages": 2,
        "last_page_fill": 0.18,
        "overflow": [
            {
                "field": "sections/sec_1/items/it_1/bullets/b_2/text",
                "needed_px": 540.5,
                "available_px": 512,
            }
        ],
        "low_contrast": [
            {"field": "header/headline", "ratio": 3.2},
            {"field": "sections/sec_2/heading", "ratio": 4.1},
        ],
        "missing_glyphs": [{"field": "header/name", "font": "Inter", "chars": "ǆ"}],
        "line_counts": {"sections/sec_1/items/it_1/bullets/b_1/text": 3},
        "empty_fields": ["header/headline"],
        "unbound_fields": ["sections/sec_3"],
        "orphan_headings": ["sections/sec_2/heading"],
        "split_items": ["sections/sec_1/items/it_1"],
    }


def test_measurement_shaped_report_parses(report: dict[str, Any]) -> None:
    parsed = RenderReport.model_validate(report)

    assert parsed.pages == 2
    assert parsed.overflow[0].needed_px > parsed.overflow[0].available_px
    assert [c.ratio for c in parsed.low_contrast] == [3.2, 4.1]
    assert parsed.line_counts["sections/sec_1/items/it_1/bullets/b_1/text"] == 3
    assert RenderReport.model_validate_json(parsed.model_dump_json()) == parsed


def test_clean_report_needs_only_the_headline_numbers() -> None:
    parsed = RenderReport(render_id=RENDER_ID, pages=1, last_page_fill=0.6)

    assert parsed.overflow == [] and parsed.line_counts == {}


@pytest.mark.parametrize("fill", [1.01, -0.1])
def test_last_page_fill_must_be_a_fraction(report: dict[str, Any], fill: float) -> None:
    report["last_page_fill"] = fill

    with pytest.raises(ValidationError):
        RenderReport.model_validate(report)


def test_report_needs_at_least_one_page(report: dict[str, Any]) -> None:
    report["pages"] = 0

    with pytest.raises(ValidationError):
        RenderReport.model_validate(report)


def test_line_counts_keys_must_be_field_paths(report: dict[str, Any]) -> None:
    report["line_counts"] = {"not a path": 1}

    with pytest.raises(ValidationError):
        RenderReport.model_validate(report)
