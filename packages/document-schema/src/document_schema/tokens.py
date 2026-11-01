from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from document_schema.base import SchemaModel

_TOKEN_NAME_PATTERN = r"^--[A-Za-z0-9-]+$"

TokenName = Annotated[str, StringConstraints(pattern=_TOKEN_NAME_PATTERN)]
"""A CSS custom property name, such as --accent"""

TokenValue = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9#%.,()'\" +_-]*$")]
"""A CSS value that cannot end its declaration or load anything"""


class Tokens(SchemaModel):
    model_config = ConfigDict(
        extra="allow",
        serialize_by_alias=True,
        json_schema_extra={"propertyNames": {"pattern": _TOKEN_NAME_PATTERN}},
    )

    __pydantic_extra__: dict[TokenName, TokenValue] = Field(init=False)

    page_margin_top: TokenValue = Field(alias="--page-margin-top")
    """Whitespace above the content on every page, one absolute length"""

    page_margin_right: TokenValue = Field(alias="--page-margin-right")
    """Whitespace right of the content on every page, one absolute length"""

    page_margin_bottom: TokenValue = Field(alias="--page-margin-bottom")
    """Whitespace below the content on every page, one absolute length"""

    page_margin_left: TokenValue = Field(alias="--page-margin-left")
    """Whitespace left of the content on every page, one absolute length"""

    font_size_body: TokenValue = Field(alias="--font-size-body")
    """Size of body text, which other text sizes are relative to"""

    line_height: TokenValue = Field(alias="--line-height")
    """Line height of body text"""

    section_gap: TokenValue = Field(alias="--section-gap")
    """Space between one section and the next"""


class ResumeTokens(Tokens):
    """Tokens of a resume or CV template, which lays out items and bullets"""

    item_gap: TokenValue = Field(alias="--item-gap")
    """Space between one item of a section and the next"""

    bullet_gap: TokenValue = Field(alias="--bullet-gap")
    """Space between one bullet of an item and the next"""


class CoverLetterTokens(Tokens):
    """Tokens of a cover letter template, whose sections are paragraphs"""
