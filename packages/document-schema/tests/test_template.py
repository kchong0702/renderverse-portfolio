from __future__ import annotations

import pytest
from pydantic import ValidationError

from document_schema import Template


def test_hash_is_stable_for_equal_input() -> None:
    first = Template(html="<p>{{x}}</p>", css="p { color: red; }")
    second = Template(html="<p>{{x}}</p>", css="p { color: red; }")

    assert first.hash == second.hash
    assert len(first.hash) == 64


def test_hash_changes_when_text_moves_between_html_and_css() -> None:
    before = Template(html="<p>a</p>", css="b")
    after = Template(html="<p>a</p>b", css="")

    assert before.hash != after.hash


def test_hash_changes_when_a_token_default_changes() -> None:
    before = Template(html="", css="", tokens={"--accent": "#111111"})
    after = Template(html="", css="", tokens={"--accent": "#222222"})

    assert before.hash != after.hash


def test_hash_ignores_token_order() -> None:
    first = Template(html="", css="", tokens={"--a": "1px", "--b": "2px"})
    second = Template(html="", css="", tokens={"--b": "2px", "--a": "1px"})

    assert first.hash == second.hash


def test_hash_is_left_out_of_the_dump() -> None:
    template = Template(html="<p>a</p>", css="p {}")

    assert template.model_dump() == {"html": "<p>a</p>", "css": "p {}", "tokens": {}}


@pytest.mark.parametrize("name", ["accent", "-accent", "--", "--has space", "--a;b"])
def test_token_names_must_be_css_custom_properties(name: str) -> None:
    with pytest.raises(ValidationError):
        Template(html="", css="", tokens={name: "red"})


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
        Template(html="", css="", tokens={"--accent": value})


def test_ordinary_token_values_are_accepted() -> None:
    tokens = {
        "--accent": "#1a2b3c",
        "--muted": "rgba(0, 0, 0, 0.6)",
        "--font-size-1": "calc(1rem + 2px)",
        "--font-body": "'Source Sans 3', sans-serif",
    }

    assert Template(html="", css="", tokens=tokens).tokens == tokens
