from typing import Any

import pytest
from conftest import rich, value
from pydantic import TypeAdapter

from document_schema import AnyDocument, AnyEdit, apply_edits

DOCUMENT = TypeAdapter(AnyDocument)
EDITS = TypeAdapter(list[AnyEdit])


def _apply(document: dict[str, Any], *edits: dict[str, Any]) -> Any:
    return apply_edits(DOCUMENT.validate_python(document), EDITS.validate_python(edits))


def _block(document: Any, block_id: str) -> Any:
    return next(block for block in document.content.blocks if block.id == block_id)


def test_update_field_replaces_a_nested_value(resume):
    edited = _apply(
        resume,
        {
            "kind": "update_field",
            "path": "blocks/exp/items/acme/role",
            "value": value("Staff Engineer"),
        },
    )

    assert _block(edited, "exp").items[0].role.text == "Staff Engineer"


def test_update_field_clears_an_optional_field(resume):
    edited = _apply(
        resume,
        {"kind": "update_field", "path": "blocks/profile/headline", "value": None},
    )

    assert _block(edited, "profile").headline is None


def test_update_field_cannot_clear_a_required_field(resume):
    with pytest.raises(ValueError, match="role"):
        _apply(
            resume,
            {
                "kind": "update_field",
                "path": "blocks/exp/items/acme/role",
                "value": None,
            },
        )


def test_insert_item_puts_a_bullet_after_another(resume):
    edited = _apply(
        resume,
        {
            "kind": "insert_item",
            "parent": "blocks/exp/items/acme/bullets",
            "after": "b1",
            "item": {"id": "b2", "text": rich("Cut deploy time by half.")},
        },
    )

    bullets = _block(edited, "exp").items[0].bullets
    assert [bullet.id for bullet in bullets] == ["b1", "b2"]


def test_insert_item_is_checked_against_its_list(resume):
    with pytest.raises(ValueError, match="text"):
        _apply(
            resume,
            {
                "kind": "insert_item",
                "parent": "blocks/exp/items/acme/bullets",
                "item": {"id": "b2"},
            },
        )


def test_insert_block_goes_after_the_named_block(resume):
    edited = _apply(
        resume,
        {
            "kind": "insert_block",
            "after": "sum",
            "block": {"kind": "languages", "id": "lang", "items": []},
        },
    )

    ids = [block.id for block in edited.content.blocks]
    assert ids.index("lang") == ids.index("sum") + 1


def test_move_puts_a_block_first(resume):
    edited = _apply(resume, {"kind": "move", "path": "blocks/sk"})

    assert edited.content.blocks[0].id == "sk"


def test_delete_removes_a_list_item(resume):
    edited = _apply(resume, {"kind": "delete", "path": "blocks/contacts/items/c2"})

    assert [item.id for item in _block(edited, "contacts").items] == ["c1"]


def test_delete_of_a_placed_block_fails_until_the_layout_drops_it(resume):
    with pytest.raises(ValueError, match="unknown blocks"):
        _apply(resume, {"kind": "delete", "path": "blocks/sk"})


def test_visibility_and_design_edits(resume):
    design = {**resume["design"], "accent": "#336699"}

    edited = _apply(
        resume,
        {"kind": "update_visibility", "block": "photo", "hidden": True},
        {"kind": "update_design", "design": design},
    )

    assert _block(edited, "photo").hidden
    assert edited.design.accent == "#336699"


def test_later_edits_see_earlier_ones(resume):
    edited = _apply(
        resume,
        {
            "kind": "insert_item",
            "parent": "blocks/exp/items/acme/bullets",
            "item": {"id": "b0", "text": rich("Joined as the first hire.")},
        },
        {"kind": "move", "path": "blocks/exp/items/acme/bullets/b0", "after": "b1"},
    )

    bullets = _block(edited, "exp").items[0].bullets
    assert [bullet.id for bullet in bullets] == ["b1", "b0"]


@pytest.mark.parametrize(
    "edit",
    [
        {"kind": "delete", "path": "blocks/nope"},
        {"kind": "update_field", "path": "blocks/exp/items/acme/nope", "value": None},
        {"kind": "move", "path": "blocks/exp/items/acme/bullets/b1", "after": "nope"},
        {"kind": "insert_item", "parent": "blocks/exp/items/acme/role", "item": {}},
        {"kind": "update_visibility", "block": "nope", "hidden": True},
        {"kind": "update_field", "path": "blocks/exp/items/acme", "value": None},
    ],
)
def test_a_path_that_isnt_there_is_refused(resume, edit):
    with pytest.raises(ValueError, match="not found|not a list|not a field"):
        _apply(resume, edit)


def test_the_original_document_is_unchanged(resume):
    document = DOCUMENT.validate_python(resume)

    apply_edits(
        document, EDITS.validate_python([{"kind": "move", "path": "blocks/sk"}])
    )

    assert document.content.blocks[0].id == "profile"
