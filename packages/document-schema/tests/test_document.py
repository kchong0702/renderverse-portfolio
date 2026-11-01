from __future__ import annotations

import copy
from functools import reduce
from typing import Any

import pytest
from conftest import FONT_SHA, LAYOUT_TOKENS
from pydantic import ValidationError

from document_schema import (
    DOCUMENT_ADAPTER,
    CoverLetterDocument,
    DocumentKind,
    PageSize,
    ResumeDocument,
    SectionKind,
)


def test_resume_round_trips_through_json_unchanged(resume: dict[str, Any]) -> None:
    document = DOCUMENT_ADAPTER.validate_python(resume)

    dumped = document.model_dump_json()
    restored = DOCUMENT_ADAPTER.validate_json(dumped)

    assert restored == document
    assert restored.model_dump_json() == dumped


def test_resume_exposes_the_content_a_consumer_reads(resume: dict[str, Any]) -> None:
    document = DOCUMENT_ADAPTER.validate_python(resume)

    assert document.kind is DocumentKind.RESUME
    assert document.format == "document/v1"
    experience, skills = document.content.sections
    assert experience.kind is SectionKind.EXPERIENCE
    assert experience.items[0].bullets[1].text.text == "Annotated Menabrea's notes"
    assert [t.text.text for t in skills.tags] == ["Mathematics", "Punch cards"]
    assert experience.items[0].tags[0].text.text == "Punch cards"
    assert experience.items[0].links[0].url.text == "https://github.com/ada/engine"
    assert document.presentation.fonts[0].sha256 == FONT_SHA


def test_cover_letter_fits_headingless_paragraph_sections(
    cover_letter: dict[str, Any],
) -> None:
    document = DOCUMENT_ADAPTER.validate_python(cover_letter)

    assert document.kind is DocumentKind.COVER_LETTER
    assert all(s.heading is None for s in document.content.sections)
    assert [s.text.text for s in document.content.sections if s.text] == [
        "Dear hiring manager,",
        "I would like to apply for the role.",
    ]
    assert document.presentation.page_size is PageSize.A4
    assert document.assets == {}


@pytest.mark.parametrize(
    ("kind", "document_class"),
    [
        ("resume", ResumeDocument),
        ("cv", ResumeDocument),
        ("cover_letter", CoverLetterDocument),
    ],
)
def test_kind_picks_the_document_and_its_tokens(
    resume: dict[str, Any], kind: str, document_class: type
) -> None:
    resume["kind"] = kind

    assert type(DOCUMENT_ADAPTER.validate_python(resume)) is document_class


@pytest.mark.parametrize("token", ["--item-gap", "--bullet-gap"])
def test_a_resume_template_must_declare_item_and_bullet_gaps(
    resume: dict[str, Any], token: str
) -> None:
    del resume["template"]["tokens"][token]

    with pytest.raises(ValidationError, match=token):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_a_cover_letter_template_needs_only_the_shared_layout_tokens(
    cover_letter: dict[str, Any],
) -> None:
    document = DOCUMENT_ADAPTER.validate_python(cover_letter)

    assert document.template.tokens.model_dump() == LAYOUT_TOKENS


def _list_at(data: dict[str, Any], path: tuple[str | int, ...]) -> list[Any]:
    return reduce(lambda node, key: node[key], path, data["content"])


@pytest.mark.parametrize(
    "path",
    [
        ("header", "contact"),
        ("sections",),
        ("sections", 0, "items"),
        ("sections", 0, "items", 0, "details"),
        ("sections", 0, "items", 0, "bullets"),
        ("sections", 0, "items", 0, "tags"),
        ("sections", 0, "items", 0, "links"),
        ("sections", 1, "tags"),
    ],
    ids=lambda p: "/".join(map(str, p)),
)
def test_duplicate_sibling_ids_are_rejected(
    resume: dict[str, Any], path: tuple[str | int, ...]
) -> None:
    siblings = _list_at(resume, path)
    siblings.append(copy.deepcopy(siblings[0]))

    with pytest.raises(ValidationError, match=f"duplicate id {siblings[0]['id']!r}"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_the_same_id_in_different_lists_is_accepted(resume: dict[str, Any]) -> None:
    sections = resume["content"]["sections"]
    resume["content"]["header"]["contact"][0]["id"] = "same"
    sections[0]["id"] = "same"
    sections[0]["items"][0]["id"] = "same"
    sections[0]["items"][0]["details"][0]["id"] = "same"
    sections[0]["items"][0]["bullets"][0]["id"] = "same"
    sections[0]["items"][0]["tags"][0]["id"] = "same"
    sections[0]["items"][0]["links"][0]["id"] = "same"
    sections[1]["tags"][0]["id"] = "same"

    DOCUMENT_ADAPTER.validate_python(resume)


@pytest.mark.parametrize(
    "url", ["http://ada.dev", "https://github.com/ada/engine?tab=readme#notes"]
)
def test_http_link_urls_are_accepted(resume: dict[str, Any], url: str) -> None:
    resume["content"]["sections"][0]["items"][0]["links"][0]["url"]["text"] = url

    DOCUMENT_ADAPTER.validate_python(resume)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "github.com/ada/engine",
        "ftp://ada.dev/notes",
        'https://ada.dev/"onmouseover="x',
        "https://ada.dev/a b",
    ],
)
def test_link_urls_a_template_cannot_safely_use_as_href_are_rejected(
    resume: dict[str, Any], url: str
) -> None:
    resume["content"]["sections"][0]["items"][0]["links"][0]["url"]["text"] = url

    with pytest.raises(ValidationError, match="must be an absolute http"):
        DOCUMENT_ADAPTER.validate_python(resume)


@pytest.mark.parametrize("bad_id", ["", "a/b", "has space", "ü"])
def test_ids_that_cannot_appear_in_a_field_path_are_rejected(
    resume: dict[str, Any], bad_id: str
) -> None:
    resume["content"]["sections"][0]["id"] = bad_id

    with pytest.raises(ValidationError):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_unknown_fields_are_rejected_at_every_level(resume: dict[str, Any]) -> None:
    top = {**resume, "extra": 1}
    nested = copy.deepcopy(resume)
    nested["content"]["header"]["name"]["colour"] = "red"

    for bad in (top, nested):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            DOCUMENT_ADAPTER.validate_python(bad)


def test_font_referencing_a_missing_asset_is_rejected(resume: dict[str, Any]) -> None:
    resume["assets"] = {}

    with pytest.raises(ValidationError, match="font 'Inter' asset a+ is not in the"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_photo_must_be_one_of_the_assets(resume: dict[str, Any]) -> None:
    photo_sha = "c" * 64
    resume["content"]["header"]["photo"] = photo_sha

    with pytest.raises(ValidationError, match="photo asset c+ is not in the"):
        DOCUMENT_ADAPTER.validate_python(resume)

    resume["assets"][photo_sha] = {
        "media_type": "image/jpeg",
        "uri": "assets/photo.jpg",
    }
    document = DOCUMENT_ADAPTER.validate_python(resume)
    assert document.assets[photo_sha].uri == "assets/photo.jpg"


@pytest.mark.parametrize("media_type", ["video/mp4", "image/svg+xml", "font/ttf"])
def test_assets_the_renderer_cannot_embed_are_rejected(
    resume: dict[str, Any], media_type: str
) -> None:
    resume["assets"][FONT_SHA]["media_type"] = media_type

    with pytest.raises(ValidationError):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_font_must_point_at_a_woff2_asset(resume: dict[str, Any]) -> None:
    resume["assets"][FONT_SHA]["media_type"] = "image/png"

    with pytest.raises(ValidationError, match="is image/png, not font/woff2"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_photo_must_point_at_an_image_asset(resume: dict[str, Any]) -> None:
    resume["content"]["header"]["photo"] = FONT_SHA

    with pytest.raises(
        ValidationError,
        match="photo asset a+ is font/woff2, not image/jpeg or image/png or image/webp",
    ):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_template_image_must_be_one_of_the_assets(resume: dict[str, Any]) -> None:
    logo_sha = "d" * 64
    resume["template"]["css"] += f" .logo {{ background: url(asset:{logo_sha}); }}"

    with pytest.raises(ValidationError, match="template image asset d+ is not in the"):
        DOCUMENT_ADAPTER.validate_python(resume)

    resume["assets"][logo_sha] = {"media_type": "image/png", "uri": "assets/logo.png"}
    DOCUMENT_ADAPTER.validate_python(resume)


def test_template_cannot_use_a_font_as_an_image(resume: dict[str, Any]) -> None:
    resume["template"]["html"] += f'<img src="asset:{FONT_SHA}">'

    with pytest.raises(ValidationError, match="template image asset a+ is font/woff2"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_token_override_must_name_a_template_token(resume: dict[str, Any]) -> None:
    resume["presentation"]["token_overrides"] = {"--acent": "#0f766e"}

    with pytest.raises(ValidationError, match="names no template token"):
        DOCUMENT_ADAPTER.validate_python(resume)


@pytest.mark.parametrize("key", ["A" * 64, "a" * 63, "inter-400.woff2"])
def test_asset_keys_that_are_not_a_sha256_are_rejected(
    resume: dict[str, Any], key: str
) -> None:
    resume["assets"][key] = resume["assets"].pop(FONT_SHA)

    with pytest.raises(ValidationError, match="String should match pattern"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_hidden_id_must_name_a_section(resume: dict[str, Any]) -> None:
    resume["presentation"]["hidden"] = ["sec_2"]
    DOCUMENT_ADAPTER.validate_python(resume)

    resume["presentation"]["hidden"] = ["sec_9"]
    with pytest.raises(ValidationError, match="names no section"):
        DOCUMENT_ADAPTER.validate_python(resume)


def test_unsupported_format_version_is_rejected(resume: dict[str, Any]) -> None:
    resume["format"] = "document/v2"

    with pytest.raises(ValidationError):
        DOCUMENT_ADAPTER.validate_python(resume)
