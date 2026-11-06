import pytest
from conftest import SIGNATURE, rich, value
from pydantic import ValidationError

from document_schema import Changeset


def changeset(*edits: dict) -> dict:
    return {
        "id": "cs1",
        "agent": "career-consultant",
        "reason": "Matches the posting",
        "edits": list(edits),
    }


def test_sourced_agent_wording_is_accepted() -> None:
    edit = {
        "op": "set_text",
        "path": "blocks/sum/text",
        "value": {"html": "New summary", "src": ["fact:k8s"]},
    }

    assert Changeset(**changeset(edit)).edits[0].op == "set_text"


@pytest.mark.parametrize("src", [[], ["user:blocks/sum"], ["agent:cs0"]])
def test_agent_wording_must_cite_a_fact_or_the_pdf(src: list[str]) -> None:
    edit = {
        "op": "set_text",
        "path": "blocks/sum/text",
        "value": {"html": "Invented", "src": src},
    }

    with pytest.raises(ValidationError, match="must cite"):
        Changeset(**changeset(edit))


def test_the_agent_cannot_add_a_photo() -> None:
    edit = {
        "op": "insert_block",
        "block": {"kind": "photo", "id": "photo", "file": "c" * 64},
    }

    with pytest.raises(ValidationError, match="photo"):
        Changeset(**changeset(edit))


def test_the_agent_cannot_add_a_signature() -> None:
    block = {
        "kind": "letter",
        "id": "letter",
        "greeting": value("Dear team,"),
        "paragraphs": [{"id": "p1", "text": rich("Hello.")}],
        "closing": value("Regards,"),
        "signature": SIGNATURE,
    }

    with pytest.raises(ValidationError, match="signature"):
        Changeset(**changeset({"op": "insert_block", "block": block}))


def test_a_changeset_has_at_least_one_edit() -> None:
    with pytest.raises(ValidationError):
        Changeset(**changeset())


def test_every_edit_kind_reads_by_its_op() -> None:
    edits = [
        {"op": "insert_item", "parent": "blocks/exp/items", "item": {"id": "x"}},
        {"op": "move", "path": "blocks/exp/items/acme", "after": None},
        {"op": "delete", "path": "blocks/sk"},
        {"op": "place", "block": "sk", "region": "side"},
        {"op": "set_hidden", "block": "sk", "hidden": True},
        {"op": "set_design", "design": {"line_spacing": 1.2}},
    ]

    assert [edit.op for edit in Changeset(**changeset(*edits)).edits] == [
        edit["op"] for edit in edits
    ]


def test_a_design_change_outside_the_safe_range_is_rejected() -> None:
    edit = {"op": "set_design", "design": {"line_spacing": 3}}

    with pytest.raises(ValidationError):
        Changeset(**changeset(edit))
