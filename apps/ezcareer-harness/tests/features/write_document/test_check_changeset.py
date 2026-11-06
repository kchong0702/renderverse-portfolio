import json
from pathlib import Path
from typing import Any

import pytest
from document_schema import AnyDocument, Changeset
from pydantic import TypeAdapter

from src.features.write_document.checks import check_changeset

FIXTURES = Path(__file__).parent / "fixtures"
DOCUMENT = TypeAdapter(AnyDocument).validate_python(
    json.loads((FIXTURES / "resume.json").read_text())
)
SOURCES = {
    line["id"]: line["text"]
    for line in json.loads((FIXTURES / "lines.json").read_text())
} | {
    f"fact:{fact['id']}": fact["text"]
    for fact in json.loads((FIXTURES / "facts.json").read_text())
}


def _check(*edits: dict[str, Any]) -> list[tuple[str, str]]:
    changeset = Changeset(
        id="cs1",
        agent="career-consultant",
        reason="Matches the posting",
        edits=list(edits),
    )
    return [
        (error.rule, error.at)
        for error in check_changeset(DOCUMENT, changeset, SOURCES)
    ]


def _bullet(html: str, *src: str) -> dict[str, Any]:
    return {
        "kind": "update_field",
        "path": "blocks/experience/items/lumen/bullets/queue/text",
        "value": {"html": html, "src": list(src)},
    }


def test_a_reworded_bullet_that_keeps_its_facts_passes():
    assert _check(_bullet("Moved 30 services onto a new message queue.", "p1.s8")) == []


def test_a_new_skill_needs_a_fact_that_names_it():
    reworded = "Led the migration of 30 services to Kubernetes."

    assert _check(_bullet(reworded, "p1.s8")) == [("unsupported", "edits/0/value")]
    assert _check(_bullet(reworded, "p1.s8", "fact:k8s")) == []


def test_an_invented_number_is_unsupported():
    assert _check(_bullet("Led the migration of 45 services.", "p1.s8")) == [
        ("unsupported", "edits/0/value")
    ]


def test_a_new_skill_tag_must_be_named_by_its_source():
    edit = {
        "kind": "insert_item",
        "parent": "blocks/skills/items/languages/items",
        "after": "postgres",
        "item": {"id": "rust", "text": {"text": "Rust", "src": ["p1.s14"]}},
    }

    assert _check(edit) == [("unsupported", "edits/0/item/text")]


def test_a_certification_backed_by_a_fact_passes():
    edit = {
        "kind": "insert_block",
        "after": "skills",
        "block": {
            "kind": "certifications",
            "id": "certs",
            "items": [
                {
                    "id": "aws",
                    "name": {
                        "text": "AWS Certified Solutions Architect",
                        "src": ["fact:aws-cert"],
                    },
                    "date": {
                        "text": {"text": "2023", "src": ["fact:aws-cert"]},
                        "start": "2023",
                    },
                }
            ],
        },
    }

    assert _check(edit) == []


@pytest.mark.parametrize("src", ["p9.s1", "fact:invented", "user:blocks/summary"])
def test_inserted_text_must_cite_a_real_line_or_fact(src):
    edit = {
        "kind": "insert_item",
        "parent": "blocks/experience/items/lumen/bullets",
        "item": {"id": "new", "text": {"html": "Mentored engineers.", "src": [src]}},
    }

    assert _check(edit) == [("unknown_source", "edits/0/item/text")]


def test_inserted_text_must_cite_something():
    edit = {
        "kind": "insert_item",
        "parent": "blocks/experience/items/lumen/bullets",
        "item": {"id": "new", "text": {"html": "Mentored engineers.", "src": []}},
    }

    assert _check(edit) == [("uncited", "edits/0/item/text")]


@pytest.mark.parametrize(
    "edit",
    [
        {"kind": "delete", "path": "blocks/photo"},
        {"kind": "update_visibility", "block": "photo", "hidden": True},
    ],
)
def test_the_photo_is_locked(edit):
    assert _check(edit) == [("locked", "edits")]


def test_moves_and_deletes_of_other_content_pass():
    assert (
        _check(
            {"kind": "move", "path": "blocks/experience/items/lumen/bullets/latency"},
            {"kind": "delete", "path": "blocks/experience/items/bayu/bullets/api"},
        )
        == []
    )


def test_an_edit_that_cannot_be_applied_is_reported():
    assert _check({"kind": "delete", "path": "blocks/education"}) == [
        ("not_applicable", "edits")
    ]


def test_the_rules_on_agent_changesets_still_apply():
    with pytest.raises(ValueError, match="must cite"):
        _check(_bullet("Moved 30 services onto a new message queue."))
