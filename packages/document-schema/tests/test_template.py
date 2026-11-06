from typing import Any, get_args

import pytest
from pydantic import TypeAdapter, ValidationError

from document_schema import AnyBlock, AnyLetterBlock, BlockKind, TemplateSpec


@pytest.fixture
def sidebar_band() -> dict[str, Any]:
    return {
        "id": "sidebar-band",
        "name": "Sidebar band",
        "description": "An accent band down the page",
        "kinds": ["resume", "cv"],
        "body_font": "inter",
        "heading_font": "inter",
        "accent": "#1F4E79",
        "regions": {
            "side": {
                "area": {"column": 1, "span": 4},
                "fill": "accent",
                "contacts": "labelled",
                "skills": "outline-pills",
            },
            "main": {"area": {"column": 5, "span": 8}, "entry": "dates-left"},
        },
        "home": {"default": "main", "photo": "side", "profile": "side"},
    }


def test_a_template_reads_its_regions_and_homes(sidebar_band: dict) -> None:
    template = TemplateSpec(**sidebar_band)

    assert (template.regions["side"].skills, template.home["photo"]) == (
        "outline-pills",
        "side",
    )


def test_block_kinds_match_the_blocks_documents_hold() -> None:
    kinds = {
        TypeAdapter(block).json_schema()["properties"]["kind"]["const"]
        for union in (AnyBlock, AnyLetterBlock)
        for block in get_args(get_args(union)[0])
    }

    assert kinds == set(BlockKind)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"home": {"photo": "side"}}, "no default"),
        ({"home": {"default": "top"}}, "missing regions"),
        (
            {"regions": {"main": {}, "side": {"area": {"column": 9, "span": 4}}}},
            "overlap",
        ),
        ({"regions": {"main": {"area": {"column": 6, "span": 8}}}}, "12th column"),
        ({"regions": {"main": {"area": {"row": 3, "rows": 3}}}}, "4th row"),
        (
            {
                "regions": {
                    "main": {"area": {"row": 1}},
                    "side": {"area": {"row": 2}},
                }
            },
            "must reach the last row",
        ),
    ],
)
def test_a_template_that_cannot_lay_out_is_rejected(
    sidebar_band: dict, change: dict, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        TemplateSpec(**{**sidebar_band, **change})


def test_a_template_never_takes_markup(sidebar_band: dict) -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        TemplateSpec(**sidebar_band, css="body { color: red }")
