from typing import Any

import pytest
from conftest import rich, value
from pydantic import TypeAdapter

from document_schema import AnyDocument, AnyEdit, Changeset, apply_edits

DOCUMENT = TypeAdapter(AnyDocument)
EDITS = TypeAdapter(list[AnyEdit])


def _apply(document: dict[str, Any], *edits: dict[str, Any]) -> Any:
    return apply_edits(DOCUMENT.validate_python(document), EDITS.validate_python(edits))


def _block(document: Any, block_id: str) -> Any:
    return next(block for block in document.content.blocks if block.id == block_id)


def _at(node: Any, path: str) -> Any:
    for key in path.split("/"):
        node = (
            next(item for item in node if item["id"] == key)
            if isinstance(node, list)
            else node[key]
        )
    return node


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
    with pytest.raises(ValueError, match="bullets"):
        _apply(
            resume,
            {
                "kind": "insert_item",
                "parent": "blocks/exp/items/acme/bullets",
                "item": {"id": "go", "text": value("Go")},
            },
        )


@pytest.mark.parametrize(
    ("document", "section", "parent", "item"),
    [
        (
            "resume",
            None,
            "blocks/contacts/items",
            {"id": "c3", "kind": "linkedin", "value": value("linkedin.com/in/kc")},
        ),
        (
            "resume",
            None,
            "blocks/exp/items",
            {"id": "globex", "role": value("Engineer"), "company": value("Globex")},
        ),
        (
            "resume",
            "education",
            "blocks/new/items",
            {"id": "bsc", "degree": value("BSc"), "school": value("UM")},
        ),
        (
            "resume",
            "projects",
            "blocks/new/items",
            {
                "id": "folio",
                "name": value("Folio"),
                "tags": [{"id": "ts", "text": value("TypeScript")}],
            },
        ),
        (
            "resume",
            None,
            "blocks/sk/items",
            {"id": "s2", "items": [{"id": "go", "text": value("Go")}]},
        ),
        (
            "resume",
            "languages",
            "blocks/new/items",
            {"id": "ms", "language": value("Malay"), "fluency": value("Native")},
        ),
        (
            "resume",
            "certifications",
            "blocks/new/items",
            {"id": "aws", "name": value("AWS Solutions Architect")},
        ),
        (
            "resume",
            "awards",
            "blocks/new/items",
            {"id": "dean", "title": value("Dean")},
        ),
        (
            "resume",
            "publications",
            "blocks/new/items",
            {"id": "paper", "title": value("Queues"), "authors": [value("K Chong")]},
        ),
        (
            "resume",
            "custom",
            "blocks/new/items",
            {"id": "vol", "title": value("Volunteer"), "location": value("KL")},
        ),
        (
            "resume",
            None,
            "blocks/exp/items/acme/bullets",
            {"id": "b2", "text": rich("Cut deploy time by half.")},
        ),
        (
            "resume",
            None,
            "blocks/exp/items/acme/links",
            {
                "id": "site",
                "url": value("https://acme.example"),
                "label": value("Acme"),
            },
        ),
        ("resume", None, "blocks/sk/items/s1/items", {"id": "go", "text": value("Go")}),
        (
            "letter",
            None,
            "blocks/letter/paragraphs",
            {"id": "p2", "text": rich("I build payment systems.")},
        ),
    ],
)
def test_an_inserted_item_of_each_kind_survives_a_stored_changeset(
    request, document, section, parent, item
):
    block = {"kind": section, "id": "new", "items": []}
    edits = [{"kind": "insert_block", "block": block}] if section else []
    edits.append({"kind": "insert_item", "parent": parent, "item": item})
    stored = Changeset(
        id="cs1", agent="career-consultant", reason="Adds an item", edits=edits
    ).model_dump_json()

    edited = apply_edits(
        DOCUMENT.validate_python(request.getfixturevalue(document)),
        Changeset.model_validate_json(stored).edits,
    )

    content = DOCUMENT.dump_python(edited, mode="json", exclude_defaults=True)
    assert _at(content["content"], f"{parent}/{item['id']}") == item


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
    layouts = [{"template": "classic", "region": "main", "blocks": ["sk", "exp"]}]
    design = {**resume["design"], "accent": "#336699", "layouts": layouts}

    edited = _apply(
        resume,
        {"kind": "update_visibility", "block": "photo", "hidden": True},
        {"kind": "update_design", "design": design},
    )

    assert _block(edited, "photo").hidden
    assert edited.design.accent == "#336699"
    assert edited.design.model_dump(mode="json")["layouts"] == layouts


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
        {
            "kind": "insert_item",
            "parent": "blocks/exp/items/acme/role",
            "item": {"id": "b2", "text": rich("Cut deploy time by half.")},
        },
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


def test_the_edits_are_unchanged_by_deleting_inside_an_inserted_item(resume):
    document = DOCUMENT.validate_python(resume)
    edits = EDITS.validate_python(
        [
            {
                "kind": "insert_item",
                "parent": "blocks/exp/items",
                "item": {
                    "id": "globex",
                    "role": value("Engineer"),
                    "company": value("Globex"),
                    "bullets": [
                        {"id": "g1", "text": rich("Built the billing service.")},
                        {"id": "g2", "text": rich("Ran the on-call rota.")},
                    ],
                },
            },
            {"kind": "delete", "path": "blocks/exp/items/globex/bullets/g2"},
        ]
    )

    first = apply_edits(document, edits)
    second = apply_edits(document, edits)

    assert second == first
    assert [bullet.id for bullet in _block(second, "exp").items[0].bullets] == ["g1"]
