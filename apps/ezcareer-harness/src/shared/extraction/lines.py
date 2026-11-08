import io

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

from src.shared.extraction.exceptions import UnreadableFile
from src.shared.extraction.types import Line


def extract_lines(pdf: bytes) -> list[Line]:
    """Reads a PDF's text lines in reading order, keeping columns apart"""
    lines: list[Line] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf), laparams={"all_texts": True}) as document:
            for page in document.pages:
                lines += [
                    Line(
                        id=f"p{page.page_number}.s{number}",
                        text=obj["text"].strip(),
                        page=page.page_number,
                        x0=obj["x0"],
                        top=obj["top"],
                        x1=obj["x1"],
                        bottom=obj["bottom"],
                    )
                    for number, obj in enumerate(
                        (
                            found
                            for found in page.objects.get("textlinehorizontal", [])
                            if found["text"].strip()
                        ),
                        start=1,
                    )
                ]
    except PdfminerException as error:
        raise UnreadableFile("the file is not a readable PDF") from error
    if not lines:
        raise UnreadableFile(
            "the PDF has no text layer; upload the original file instead of a scan"
        )
    return lines
