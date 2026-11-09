import pytest
from pydantic import ValidationError

from document_schema import OrphanHeading, Report, SplitEntry

RENDER = "d" * 64


def test_warnings_read_by_their_kind() -> None:
    report = Report(
        render_id=RENDER,
        pages=2,
        last_page_fill=0.4,
        spans=[{"block": "exp", "first_page": 1, "last_page": 2}],
        warnings=[
            {"kind": "split_entry", "path": "blocks/exp/items/acme", "pages": (1, 2)},
            {"kind": "orphan_heading", "block": "edu", "page": 1},
        ],
    )

    assert [type(w) for w in report.warnings] == [SplitEntry, OrphanHeading]


def test_a_span_cannot_end_before_it_starts() -> None:
    with pytest.raises(ValidationError, match="ends before"):
        Report(
            render_id=RENDER,
            pages=2,
            last_page_fill=0.5,
            spans=[{"block": "exp", "first_page": 2, "last_page": 1}],
        )
