from pydantic import JsonValue

from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.nodes import verify
from src.features.import_document.schemas import LookSuggestion, ResumeImport
from src.shared.checks import CheckError, CheckRule
from src.shared.extraction import Line


def make_lines(*texts: str) -> list[Line]:
    """One line per text on page 1, numbered from p1.s1"""
    return [
        Line(
            id=f"p1.s{n}",
            text=text,
            page=1,
            x0=0,
            top=10 * n,
            x1=100,
            bottom=10 * n + 8,
        )
        for n, text in enumerate(texts, start=1)
    ]


SUGGESTION = LookSuggestion(template="serif", columns=1, traits=[])

LINES = make_lines(
    "K R I S T I  L A A R",
    "EXPERIENCE",
    "• Led a team of five",
    "nurses at Wholeness",
    "1",
)


def value(text: str, *src: str) -> dict[str, JsonValue]:
    """A Value citing src"""
    return {"text": text, "src": list(src)}


def reply(
    *,
    bullet: dict[str, JsonValue] | None = None,
    skipped: tuple[str, ...] = ("p1.s5",),
    first: str = "profile",
) -> dict[str, JsonValue]:
    """A faithful reply for LINES, with its bullet, skipped lines or first block
    replaced"""
    profile: dict[str, JsonValue] = {
        "kind": "profile",
        "id": "profile",
        "name": value("Kristi Laar", "p1.s1"),
    }
    experience: dict[str, JsonValue] = {
        "kind": "experience",
        "id": "experience",
        "heading": value("Experience", "p1.s2"),
        "items": [
            {
                "id": "wholeness",
                "role": value("Nurse", "p1.s4"),
                "company": value("Wholeness", "p1.s4"),
                "bullets": [
                    {
                        "id": "team",
                        "text": bullet
                        or {
                            "html": "Led a team of <b>five nurses</b>",
                            "src": ["p1.s4", "p1.s3"],
                        },
                    }
                ],
            }
        ],
    }
    blocks = [profile, experience] if first == "profile" else [experience, profile]
    return {"blocks": blocks, "skipped": list(skipped)}


def check(
    draft: dict[str, JsonValue],
    configurations: ImportResumeConfigurations,
    lines: list[Line] = LINES,
) -> list[CheckError]:
    """What verify finds in a reply to lines"""
    return verify(
        {
            "structured_response": ResumeImport.model_validate(draft),
            "lines": lines,
            "suggestion": SUGGESTION,
        },
        configurations,
    )["errors"]


def test_a_faithful_reply_passes_and_becomes_the_draft_in_the_suggested_template(
    configurations: ImportResumeConfigurations,
):
    result = verify(
        {
            "structured_response": ResumeImport.model_validate(reply()),
            "lines": LINES,
            "suggestion": SUGGESTION,
        },
        configurations,
    )

    assert result["errors"] == []
    assert result["document"].design.template == "serif"
    assert (
        result["document"].content.blocks == ResumeImport.model_validate(reply()).blocks
    )


def test_a_reply_that_is_no_resume_import_fails_schema_and_asks_for_a_fix(
    configurations: ImportResumeConfigurations,
):
    result = verify(
        {
            "structured_response": None,
            "parsing_error": "the reply holds no ResumeImport",
        },
        configurations,
    )

    assert result["errors"] == [
        CheckError(
            rule=CheckRule.SCHEMA, at="", message="the reply holds no ResumeImport"
        )
    ]
    assert "the reply holds no ResumeImport" in result["messages"][0].content


def test_reworded_or_uncited_text_fails_verbatim(
    configurations: ImportResumeConfigurations,
):
    errors = check(
        reply(bullet={"html": "Managed five nurses", "src": ["p1.s3"]}),
        configurations,
    )

    assert [(e.rule, e.at) for e in errors] == [
        (CheckRule.VERBATIM, "blocks/experience/items/wholeness/bullets/team/text"),
        (CheckRule.COVERAGE, "blocks"),
    ]
    assert "'Managed five nurses' is not the text of p1.s3" in errors[0].message


def test_citing_something_that_is_not_a_line_fails_verbatim(
    configurations: ImportResumeConfigurations,
):
    errors = check(
        reply(bullet={"html": "Led a team", "src": ["p9.s1"]}),
        configurations.model_copy(update={"checks": ["verbatim"]}),
    )

    assert [e.message for e in errors] == ["cites p9.s1, which are not lines"]


def test_a_value_without_text_fails_verbatim(
    configurations: ImportResumeConfigurations,
):
    errors = check(
        reply(bullet={"html": "•", "src": ["p1.s3"]}),
        configurations.model_copy(update={"checks": ["verbatim"]}),
    )

    assert [e.message for e in errors] == ["has no text"]


def test_a_line_neither_cited_nor_skipped_fails_coverage(
    configurations: ImportResumeConfigurations,
):
    errors = check(reply(skipped=("p7.s7",)), configurations)

    assert [(e.rule, e.at) for e in errors] == [
        (CheckRule.COVERAGE, "skipped"),
        (CheckRule.COVERAGE, "blocks"),
    ]
    assert errors[0].message == "p7.s7 are not lines"
    assert "p1.s5 '1' (not cited)" in errors[1].message


def test_a_value_that_drops_words_of_its_lines_fails_coverage(
    configurations: ImportResumeConfigurations,
):
    [error] = check(
        reply(bullet={"html": "Led a", "src": ["p1.s3", "p1.s4"]}),
        configurations,
    )

    assert error.rule == CheckRule.COVERAGE
    assert error.message.endswith("p1.s3 '• Led a team of five' (unused: team five)")


def test_a_value_may_drop_short_joining_words_between_cited_ones(
    configurations: ImportResumeConfigurations,
):
    lines = make_lines("Ada Lovelace", "Fellow of the Royal Society")
    draft: dict[str, JsonValue] = {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": value("Ada Lovelace", "p1.s1"),
            },
            {
                "kind": "experience",
                "id": "experience",
                "items": [
                    {
                        "id": "royal_society",
                        "role": value("Fellow", "p1.s2"),
                        "company": value("Royal Society", "p1.s2"),
                    }
                ],
            },
        ]
    }

    assert check(draft, configurations, lines) == []


def test_skipping_a_line_with_content_fails_coverage(
    configurations: ImportResumeConfigurations,
):
    errors = check(
        reply(skipped=("p1.s5", "p1.s3")),
        configurations.model_copy(update={"checks": ["coverage"]}),
    )

    assert [e.at for e in errors] == ["skipped"]
    assert "p1.s3 '• Led a team of five'" in errors[0].message


def test_coverage_allows_what_the_configurations_allow(
    configurations: ImportResumeConfigurations,
):
    lenient = configurations.model_copy(
        update={
            "checks": ["coverage"],
            "max_skipped_length": 20,
            "max_joining_word_length": 6,
        }
    )

    assert check(reply(skipped=("p1.s5", "p1.s3")), lenient) == []
    assert (
        check(reply(bullet={"html": "Led a team", "src": ["p1.s3", "p1.s4"]}), lenient)
        == []
    )


def test_dashes_quotes_and_hyphenated_breaks_still_match(
    configurations: ImportResumeConfigurations,
):
    lines = make_lines("Ada O’Brien", "2019 – 2024 project manage-", "ment lead")
    draft: dict[str, JsonValue] = {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": value("Ada O'Brien", "p1.s1"),
                "headline": value(
                    "2019 - 2024 project management lead", "p1.s2", "p1.s3"
                ),
            }
        ]
    }

    assert check(draft, configurations, lines) == []


def test_blocks_out_of_line_order_fail_order(
    configurations: ImportResumeConfigurations,
):
    errors = check(reply(first="experience"), configurations)

    assert [(e.rule, e.at) for e in errors] == [(CheckRule.ORDER, "blocks/profile")]


def test_only_the_chosen_checks_run(configurations: ImportResumeConfigurations):
    errors = check(
        reply(skipped=()),
        configurations.model_copy(update={"checks": ["verbatim", "order"]}),
    )

    assert errors == []
