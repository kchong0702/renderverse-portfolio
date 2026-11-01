from typing import Any

from document_schema import Content

from src.features.render_document.view import build_view


def test_every_value_gets_its_path_in_content_order(
    document_data: dict[str, Any],
) -> None:
    view = build_view(Content.model_validate(document_data["content"]), set())

    assert view.value_paths == [
        "header/name",
        "sections/sum/text",
        "sections/exp/heading",
        "sections/exp/items/it_1/title",
        "sections/exp/items/it_1/bullets/b_1/text",
        "sections/exp/items/it_1/bullets/b_2/text",
        "sections/exp/items/it_1/links/l_1/url",
        "sections/sk/heading",
        "sections/sk/tags/t_1/text",
        "sections/sk/tags/t_2/text",
    ]
    bullet = view.content.sections[1].items[0].bullets[1]
    assert bullet.text.path == "sections/exp/items/it_1/bullets/b_2/text"


def test_sections_carry_a_flag_for_every_kind(document_data: dict[str, Any]) -> None:
    view = build_view(Content.model_validate(document_data["content"]), set())

    skills = view.content.sections[2]
    assert skills.is_skills is True
    assert skills.is_experience is False
    assert skills.is_summary is False


def test_unset_fields_stay_as_none_so_lookups_stop_there(
    document_data: dict[str, Any],
) -> None:
    view = build_view(Content.model_validate(document_data["content"]), set())

    item = view.content.model_dump(mode="json")["sections"][1]["items"][0]
    assert "location" in item
    assert item["location"] is None


def test_hidden_sections_are_dropped_with_their_values(
    document_data: dict[str, Any],
) -> None:
    view = build_view(Content.model_validate(document_data["content"]), {"exp"})

    assert [s.id for s in view.content.sections] == ["sum", "sk"]
    assert not any(path.startswith("sections/exp") for path in view.value_paths)
