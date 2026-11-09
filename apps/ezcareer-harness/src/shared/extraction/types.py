from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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
