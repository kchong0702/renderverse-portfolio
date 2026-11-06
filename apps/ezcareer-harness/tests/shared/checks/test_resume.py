from src.shared.checks import Check, validate_resume
from src.shared.extraction import Line


def make_lines(*texts: str) -> list[Line]:
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


LINES = make_lines(
    "K R I S T I  L A A R",
    "EXPERIENCE",
    "• Led a team of five",
    "nurses at Wholeness",
    "1",
)


def value(text: str, *src: str) -> dict:
    return {"text": text, "src": list(src)}


def reply(
    *,
    headline_src: tuple[str, ...] = (),
    bullet: dict | None = None,
    skipped=("p1.s5",),
    first="profile",
) -> dict:
    profile = {
        "kind": "profile",
        "id": "profile",
        "name": value("Kristi Laar", "p1.s1"),
    }
    experience = {
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
    return {"content": {"blocks": blocks}, "skipped": list(skipped)}


def test_a_faithful_reply_passes():
    assert validate_resume(reply(), LINES) == []


def test_a_reply_that_breaks_the_schema_fails_with_its_path():
    broken = reply()
    broken["content"]["blocks"] = broken["content"]["blocks"][1:]

    [error] = validate_resume(broken, LINES)

    assert error.check == Check.SCHEMA
    assert error.path == "content"
    assert "exactly one profile" in error.message


def test_reworded_or_uncited_text_fails_verbatim():
    errors = validate_resume(
        reply(bullet={"html": "Managed five nurses", "src": ["p1.s3"]}), LINES
    )

    assert [(e.check, e.path) for e in errors] == [
        (Check.VERBATIM, "content/blocks/experience/items/wholeness/bullets/team/text")
    ]
    assert "'Managed five nurses' is not the text of p1.s3" in errors[0].message


def test_citing_something_that_is_not_a_line_fails_verbatim():
    errors = validate_resume(
        reply(bullet={"html": "Led a team", "src": ["p9.s1"]}), LINES, [Check.VERBATIM]
    )

    assert [e.message for e in errors] == ["cites p9.s1, which are not lines"]


def test_a_line_neither_cited_nor_skipped_fails_coverage():
    errors = validate_resume(reply(skipped=("p7.s7",)), LINES)

    assert [(e.check, e.path, e.message) for e in errors] == [
        (Check.COVERAGE, "skipped", "p7.s7 are not lines"),
        (
            Check.COVERAGE,
            "content",
            "these lines are neither cited nor skipped: p1.s5 '1'",
        ),
    ]


def test_blocks_out_of_line_order_fail_order():
    errors = validate_resume(reply(first="experience"), LINES)

    assert [(e.check, e.path) for e in errors] == [
        (Check.ORDER, "content/blocks/profile")
    ]


def test_only_the_chosen_checks_run():
    assert (
        validate_resume(reply(skipped=()), LINES, [Check.VERBATIM, Check.ORDER]) == []
    )
