from __future__ import annotations

import pytest
from pydantic import ValidationError

from document_schema import FontFace, FontStyle, PageSize, Presentation

SHA = "c" * 64


def test_defaults_are_a4_with_nothing_else() -> None:
    presentation = Presentation()

    assert presentation.page_size is PageSize.A4
    assert presentation.token_overrides == {}
    assert presentation.fonts == []
    assert presentation.hidden == []


def test_token_overrides_follow_the_template_token_rules() -> None:
    with pytest.raises(ValidationError):
        Presentation(token_overrides={"--accent": "red; color: blue"})


@pytest.mark.parametrize("family", ['Inter"; } body { color: red', "Inter</style>", ""])
def test_font_family_that_could_break_out_of_css_is_rejected(family: str) -> None:
    with pytest.raises(ValidationError):
        FontFace(family=family, sha256=SHA)


@pytest.mark.parametrize("weight", [99, 901])
def test_font_weight_outside_css_range_is_rejected(weight: int) -> None:
    with pytest.raises(ValidationError):
        FontFace(family="Inter", weight=weight, sha256=SHA)


def test_font_defaults_to_regular_upright() -> None:
    font = FontFace(family="Inter", sha256=SHA)

    assert (font.weight, font.style) == (400, FontStyle.NORMAL)
