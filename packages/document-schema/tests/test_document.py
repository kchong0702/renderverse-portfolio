from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from document_schema import AnyDocument, LetterDocument, ResumeDocument

DOCUMENT = TypeAdapter(AnyDocument)


def test_a_resume_and_a_cv_read_as_resume_documents(resume: dict[str, Any]) -> None:
    assert isinstance(DOCUMENT.validate_python(resume), ResumeDocument)
    assert isinstance(
        DOCUMENT.validate_python({**resume, "kind": "cv"}), ResumeDocument
    )


def test_a_cover_letter_reads_as_a_letter_document(letter: dict[str, Any]) -> None:
    assert isinstance(DOCUMENT.validate_python(letter), LetterDocument)


def test_blocks_keep_their_kind(resume: dict[str, Any]) -> None:
    document = DOCUMENT.validate_python(resume)

    assert [block.kind for block in document.content.blocks] == [
        "profile",
        "photo",
        "contacts",
        "summary",
        "experience",
        "skills",
    ]


@pytest.mark.parametrize(
    "change",
    [
        lambda blocks: blocks.append({**blocks[3], "id": "sum2"}),
        lambda blocks: blocks.append({**blocks[0], "id": "profile2"}),
        lambda blocks: blocks.pop(0),
        lambda blocks: blocks.append({**blocks[4]}),
    ],
    ids=["two summaries", "two profiles", "no profile", "repeated id"],
)
def test_a_resume_needs_one_profile_and_unique_blocks(
    resume: dict[str, Any], change
) -> None:
    change(resume["content"]["blocks"])

    with pytest.raises(ValidationError):
        DOCUMENT.validate_python(resume)


def test_a_photo_must_be_in_the_assets(resume: dict[str, Any]) -> None:
    resume["assets"] = {}

    with pytest.raises(ValidationError, match="files not in assets"):
        DOCUMENT.validate_python(resume)


def test_a_signature_must_be_in_the_assets(letter: dict[str, Any]) -> None:
    letter["assets"] = {}

    with pytest.raises(ValidationError, match="files not in assets"):
        DOCUMENT.validate_python(letter)


def test_a_layout_places_only_blocks_that_exist(resume: dict[str, Any]) -> None:
    resume["design"]["layouts"]["sidebar-band"]["main"] = ["missing"]

    with pytest.raises(ValidationError, match="unknown blocks"):
        DOCUMENT.validate_python(resume)


def test_a_hidden_block_stays_in_the_document(resume: dict[str, Any]) -> None:
    resume["content"]["blocks"][1]["hidden"] = True

    document = DOCUMENT.validate_python(resume)

    assert document.content.blocks[1].hidden
