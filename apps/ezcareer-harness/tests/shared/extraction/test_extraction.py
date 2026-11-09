import pytest
from fpdf import FPDF

from src.shared.extraction import UnreadableFile, extract_lines
from tests.pdfs import make_pdf


def test_lines_are_numbered_per_page_in_reading_order():
    pdf = make_pdf(
        [(10, 10, "Ada Lovelace"), (10, 20, "Engineer")], [(10, 10, "Page two")]
    )

    lines = extract_lines(pdf)

    assert [(line.id, line.text, line.page) for line in lines] == [
        ("p1.s1", "Ada Lovelace", 1),
        ("p1.s2", "Engineer", 1),
        ("p2.s1", "Page two", 2),
    ]
    assert lines[0].top < lines[1].top
    assert lines[0].x0 < lines[0].x1


def test_text_inside_a_form_xobject_is_read():
    form = b"BT /F1 12 Tf 72 720 Td (Inside a form) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R"
        + b" /Resources << /XObject << /Fm1 4 0 R >> >> >>",
        b"<< /Type /XObject /Subtype /Form /BBox [0 0 612 792]"
        b" /Resources << /Font << /F1 6 0 R >> >> /Length %d >>\nstream\n%s\nendstream"
        % (len(form), form),
        b"<< /Length 8 >>\nstream\n/Fm1 Do\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = (
        b"%PDF-1.4\n"
        + b"".join(b"%d 0 obj\n%s\nendobj\n" % (i, o) for i, o in enumerate(objects, 1))
        + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )

    assert [line.text for line in extract_lines(pdf)] == ["Inside a form"]


def test_columns_are_read_one_after_the_other():
    rows = [
        ("SKILLS", "EXPERIENCE"),
        ("Python", "Senior Engineer, Acme"),
        ("Rust", "Led a team of five"),
    ]
    pdf = make_pdf(
        [(10, 30 + 5 * i, side) for i, (side, _) in enumerate(rows)]
        + [(80, 30 + 5 * i, main) for i, (_, main) in enumerate(rows)]
    )

    assert [line.text for line in extract_lines(pdf)] == [
        "SKILLS",
        "Python",
        "Rust",
        "EXPERIENCE",
        "Senior Engineer, Acme",
        "Led a team of five",
    ]


def test_a_pdf_without_text_asks_for_the_original():
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 50, 50)

    with pytest.raises(UnreadableFile, match="no text layer"):
        extract_lines(bytes(pdf.output()))


def test_a_broken_pdf_is_unreadable():
    with pytest.raises(UnreadableFile, match="not a readable PDF"):
        extract_lines(b"%PDF-1.7 broken")
