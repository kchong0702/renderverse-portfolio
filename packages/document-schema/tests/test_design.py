import pytest
from pydantic import ValidationError

from document_schema import Design


def test_the_default_design_is_classic_on_a4() -> None:
    design = Design()

    assert (design.template, design.page_size, design.layouts) == ("classic", "a4", {})


@pytest.mark.parametrize(
    "template", ["sidebar-band", "custom-0b8f7d2e-1c3a-4e5f-9a6b-7c8d9e0f1a2b"]
)
def test_a_default_or_custom_template_is_accepted(template: str) -> None:
    Design(template=template)


@pytest.mark.parametrize(
    "fields",
    [
        {"template": "Sidebar Band"},
        {"line_spacing": 2.0},
        {"margins_mm": 5},
        {"section_spacing_pt": 40},
        {"alignment": "center"},
        {"accent": "green"},
    ],
)
def test_values_outside_the_safe_range_are_rejected(fields: dict) -> None:
    with pytest.raises(ValidationError):
        Design(**fields)


def test_a_block_listed_twice_in_a_region_is_rejected() -> None:
    with pytest.raises(ValidationError, match="twice in one region"):
        Design(layouts={"classic": {"main": ["exp", "exp"]}})


def test_a_block_in_two_regions_is_rejected() -> None:
    with pytest.raises(ValidationError, match="two regions"):
        Design(layouts={"sidebar-band": {"main": ["exp"], "side": ["exp"]}})


def test_an_unknown_region_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Design(layouts={"classic": {"footer": ["exp"]}})
