import pytest
from pydantic import ValidationError

from document_schema import Date, RichValue


@pytest.mark.parametrize(
    ("html", "kept"),
    [
        (
            "<b>bold</b> <i>italic</i> <u>under</u>",
            "<b>bold</b> <i>italic</i> <u>under</u>",
        ),
        (
            '<a href="https://kelvin.dev">site</a>',
            '<a href="https://kelvin.dev">site</a>',
        ),
        (
            '<span data-size="small">fine print</span>',
            '<span data-size="small">fine print</span>',
        ),
        ('<span data-size="huge">big</span>', "<span>big</span>"),
        ('<a href="javascript:alert(1)">x</a>', "<a>x</a>"),
        ("<script>alert(1)</script>ok", "ok"),
        ('<b onclick="x()">b</b>', "<b>b</b>"),
        ("<h1>title</h1>", "title"),
    ],
)
def test_rich_text_keeps_only_formatting(html: str, kept: str) -> None:
    assert RichValue(html=html).html == kept


def test_rich_text_reads_as_plain_text() -> None:
    assert RichValue(html="R&amp;D at <b>Acme</b>").text == "R&D at Acme"


@pytest.mark.parametrize(
    ("start", "end"), [("2022", "present"), ("2022-03", "2024-11"), ("2019", None)]
)
def test_dates_take_a_year_or_a_month(start: str, end: str | None) -> None:
    Date(text={"text": "as written"}, start=start, end=end)


def test_a_malformed_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Date(text={"text": "22"}, start="22")
