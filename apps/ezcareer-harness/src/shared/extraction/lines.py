import io
from typing import Annotated

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.shared.extraction.errors import UnreadableFile

LineId = Annotated[str, StringConstraints(pattern=r"^p\d+\.s\d+$")]
"""A PDF line, such as p1.s41"""


class Line(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: LineId
    """Page and line number, counted from 1 on each page"""

    text: str
    """The line's text"""

    page: int = Field(ge=1)
    """Page it is on"""

    x0: float
    """Left edge, in points from the page's left"""

    top: float
    """Top edge, in points from the page's top"""

    x1: float
    """Right edge, in points from the page's left"""

    bottom: float
    """Bottom edge, in points from the page's top"""


def extract_lines(pdf: bytes) -> list[Line]:
    """Reads a PDF's text lines in reading order, keeping columns apart"""
    lines: list[Line] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf), laparams={"all_texts": True}) as document:
            for page in document.pages:
                texts = [
                    obj
                    for obj in page.objects.get("textlinehorizontal", [])
                    if obj["text"].strip()
                ]
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
                    for number, obj in enumerate(texts, start=1)
                ]
    except PdfminerException as error:
        raise UnreadableFile("the file is not a readable PDF") from error
    if not lines:
        raise UnreadableFile(
            "the PDF has no text layer; upload the original file instead of a scan"
        )
    return lines
