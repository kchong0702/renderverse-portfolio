import pytest
from pydantic import TypeAdapter

from document_schema import AnyEdit, ContactKind, Date, RichValue, Value

EDIT = TypeAdapter(AnyEdit)


@pytest.mark.parametrize(
    ("path", "value", "kind"),
    [
        ("blocks/exp/items/acme/role", {"text": "Staff Engineer"}, Value),
        ("blocks/sum/text", {"html": "Backend <b>engineer</b>"}, RichValue),
        (
            "blocks/exp/items/acme/dates",
            {"text": {"text": "2022 to now"}, "start": "2022", "end": "present"},
            Date,
        ),
        ("blocks/contacts/items/c2/kind", "linkedin", ContactKind),
    ],
)
def test_a_field_update_reads_its_value_as_the_field_type(
    path: str, value: object, kind: type
) -> None:
    edit = EDIT.validate_python({"kind": "update_field", "path": path, "value": value})

    assert isinstance(edit.value, kind)


def test_a_field_update_can_replace_a_list_of_values() -> None:
    edit = EDIT.validate_python(
        {
            "kind": "update_field",
            "path": "blocks/pubs/items/p1/authors",
            "value": [{"text": "A. Lovelace"}, {"text": "C. Babbage"}],
        }
    )

    assert [author.text for author in edit.value] == ["A. Lovelace", "C. Babbage"]


def test_a_field_update_can_clear_an_optional_field() -> None:
    edit = EDIT.validate_python(
        {"kind": "update_field", "path": "blocks/profile/headline", "value": None}
    )

    assert edit.value is None
