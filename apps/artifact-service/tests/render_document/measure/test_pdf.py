from src.features.render_document.measure.pdf import (
    orphan_headings,
    split_items,
)

PATHS = [
    "header/name",
    "sections/exp/heading",
    "sections/exp/items/a/title",
    "sections/exp/items/a/bullets/b_1/text",
    "sections/exp/items/b/title",
    "sections/edu/heading",
    "sections/edu/text",
]


def test_an_item_is_split_when_its_fields_span_pages() -> None:
    pages = {
        "sections/exp/items/a/title": (1, 1),
        "sections/exp/items/a/bullets/b_1/text": (1, 2),
        "sections/exp/items/b/title": (2, 2),
    }

    assert split_items(pages, PATHS) == ["sections/exp/items/a"]


def test_a_heading_is_orphaned_only_when_its_next_content_is_on_a_later_page() -> None:
    pages = {
        "sections/exp/heading": (1, 1),
        "sections/exp/items/a/title": (2, 2),
        "sections/edu/heading": (2, 2),
        "sections/edu/text": (2, 2),
    }

    assert orphan_headings(pages, PATHS) == ["sections/exp/heading"]


def test_unbound_fields_are_skipped_when_finding_the_next_content() -> None:
    pages = {
        "sections/exp/heading": (1, 1),
        "sections/exp/items/a/bullets/b_1/text": (1, 1),
    }

    assert orphan_headings(pages, PATHS) == []
    assert split_items(pages, PATHS) == []
