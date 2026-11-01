from __future__ import annotations

import pytest
from conftest import LAYOUT_TOKENS
from pydantic import ValidationError

from document_schema import Template


def test_hash_is_stable_for_equal_input() -> None:
    first = Template(html="<p>{{x}}</p>", css="p { color: red; }", tokens=LAYOUT_TOKENS)
    second = Template(
        html="<p>{{x}}</p>", css="p { color: red; }", tokens=LAYOUT_TOKENS
    )

    assert first.hash == second.hash
    assert len(first.hash) == 64


def test_hash_changes_when_text_moves_between_html_and_css() -> None:
    before = Template(html="<p>a</p>", css="b", tokens=LAYOUT_TOKENS)
    after = Template(html="<p>a</p>b", css="", tokens=LAYOUT_TOKENS)

    assert before.hash != after.hash


def test_hash_changes_when_a_token_default_changes() -> None:
    before = Template(html="", css="", tokens={**LAYOUT_TOKENS, "--accent": "#111111"})
    after = Template(html="", css="", tokens={**LAYOUT_TOKENS, "--accent": "#222222"})

    assert before.hash != after.hash


def test_hash_ignores_token_order() -> None:
    first = Template(html="", css="", tokens={**LAYOUT_TOKENS, "--a": "1px"})
    second = Template(html="", css="", tokens={"--a": "1px", **LAYOUT_TOKENS})

    assert first.hash == second.hash


def test_hash_is_left_out_of_the_dump() -> None:
    template = Template(html="<p>a</p>", css="p {}", tokens=LAYOUT_TOKENS)

    assert template.model_dump() == {
        "html": "<p>a</p>",
        "css": "p {}",
        "tokens": LAYOUT_TOKENS,
    }


@pytest.mark.parametrize("token", list(LAYOUT_TOKENS))
def test_every_layout_token_must_be_declared(token: str) -> None:
    tokens = {name: value for name, value in LAYOUT_TOKENS.items() if name != token}

    with pytest.raises(ValidationError, match=token):
        Template(html="", css="", tokens=tokens)


def test_schema_requires_layout_tokens_and_names_extra_tokens() -> None:
    schema = Template.model_json_schema()["$defs"]["Tokens"]

    assert set(schema["required"]) == set(LAYOUT_TOKENS)
    assert schema["propertyNames"] == {"pattern": "^--[A-Za-z0-9-]+$"}
    assert schema["properties"]["--section-gap"]["description"] == (
        "Space between one section and the next"
    )


@pytest.mark.parametrize("name", ["accent", "-accent", "--", "--has space", "--a;b"])
def test_token_names_must_be_css_custom_properties(name: str) -> None:
    with pytest.raises(ValidationError):
        Template(html="", css="", tokens={**LAYOUT_TOKENS, name: "red"})


@pytest.mark.parametrize(
    "value",
    [
        "red; color: blue",
        "red}",
        "{red",
        "red</style><script>",
        "red /* swallow the rest",
        "\\72 ed",
        "url(https://example.com/x.png)",
        "@import x",
    ],
)
def test_token_values_cannot_escape_a_declaration_or_fetch(value: str) -> None:
    with pytest.raises(ValidationError):
        Template(html="", css="", tokens={**LAYOUT_TOKENS, "--accent": value})


def test_ordinary_token_values_are_accepted() -> None:
    tokens = {
        **LAYOUT_TOKENS,
        "--accent": "#1a2b3c",
        "--muted": "rgba(0, 0, 0, 0.6)",
        "--font-size-1": "calc(1rem + 2px)",
        "--font-body": "'Source Sans 3', sans-serif",
    }

    assert Template(html="", css="", tokens=tokens).tokens.model_dump() == tokens
