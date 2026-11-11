from fpdf import FPDF


def make_pdf(*pages: list[tuple[float, float, str]]) -> bytes:
    """A PDF with one page per list, each text written at its x and y in mm"""
    pdf = FPDF()
    for page in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        for x, y, text in page:
            pdf.set_xy(x, y)
            pdf.cell(text=text)
    return bytes(pdf.output())
