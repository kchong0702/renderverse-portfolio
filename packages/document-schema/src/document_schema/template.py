from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from document_schema.design import TemplateId
from document_schema.document import DocumentKind
from document_schema.enums import Align, Font, Region
from document_schema.types import Colour


class BlockKind(StrEnum):
    PROFILE = "profile"
    """Name and headline"""

    PHOTO = "photo"
    """The user's photo"""

    CONTACTS = "contacts"
    """Ways to reach the person"""

    SUMMARY = "summary"
    """A short pitch"""

    EXPERIENCE = "experience"
    """Jobs"""

    EDUCATION = "education"
    """Degrees"""

    PROJECTS = "projects"
    """Projects"""

    SKILLS = "skills"
    """Skill rows"""

    LANGUAGES = "languages"
    """Spoken languages"""

    CERTIFICATIONS = "certifications"
    """Certifications"""

    AWARDS = "awards"
    """Awards"""

    PUBLICATIONS = "publications"
    """Publications"""

    CUSTOM = "custom"
    """A section the user names"""

    RECIPIENT = "recipient"
    """Who a letter is to"""

    LETTER = "letter"
    """A letter's body"""


class Fill(StrEnum):
    NONE = "none"
    """The page colour"""

    ACCENT = "accent"
    """The accent colour, with light text"""

    TINT = "tint"
    """A pale wash of the accent colour"""


class Edge(StrEnum):
    TOP = "top"
    """Above the region"""

    BOTTOM = "bottom"
    """Below the region"""

    LEFT = "left"
    """Left of the region"""

    RIGHT = "right"
    """Right of the region"""


class TitleStyle(StrEnum):
    RULE_AFTER = "rule-after"
    """Title, then a line to the end of the row"""

    RULE_BOTH = "rule-both"
    """Lines above and below the title"""

    UNDERLINE = "underline"
    """A short line under the title"""

    STRIP = "strip"
    """Title on a tinted strip"""

    SIDE_BAR = "side-bar"
    """An accent bar left of the title"""


class EntryLayout(StrEnum):
    INLINE = "inline"
    """Role and place on one line, dates on the right"""

    DATES_LEFT = "dates-left"
    """Dates in a narrow column left of the entry"""

    DATES_BELOW = "dates-below"
    """Role, place and dates stacked"""


class ContactsStyle(StrEnum):
    LINE = "line"
    """One line with separators"""

    LABELLED = "labelled"
    """One per line, under a small label"""

    ICON_TILES = "icon-tiles"
    """One per line, after an icon on a tile"""


class SkillsStyle(StrEnum):
    INLINE = "inline"
    """Comma separated"""

    OUTLINE_PILLS = "outline-pills"
    """Each skill in an outlined pill"""

    FILLED_PILLS = "filled-pills"
    """Each skill in a filled pill"""


class PhotoSpot(StrEnum):
    NONE = "none"
    """The template leaves the photo off"""

    TOP = "top"
    """Centred, on its own line"""

    START = "start"
    """Left of the blocks after it"""

    END = "end"
    """Right of the blocks after it"""


class GridArea(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    column: int = Field(1, ge=1, le=12)
    """First of the page's 12 columns it covers"""

    span: int = Field(12, ge=1, le=12)
    """Columns it covers"""

    row: int = Field(1, ge=1, le=4)
    """First row it covers; the last row grows to fill the page"""

    rows: int = Field(1, ge=1, le=4)
    """Rows it covers"""

    @model_validator(mode="after")
    def _inside_the_page(self) -> Self:
        """Rejects an area past the 12th column"""
        if self.column + self.span > 13:
            raise ValueError("an area runs past the 12th column")
        return self


class RegionSpec(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    area: GridArea = Field(default_factory=GridArea)
    """Where it sits on the page grid"""

    fill: Fill = Fill.NONE
    """Background; a fill on an area down the whole page runs onto every page"""

    divider: Edge | None = None
    """A line along one edge"""

    align: Align = Align.LEFT
    """How headings and short lines sit"""

    title: TitleStyle = TitleStyle.RULE_AFTER
    """Section title style"""

    entry: EntryLayout = EntryLayout.INLINE
    """How an entry places its dates"""

    contacts: ContactsStyle = ContactsStyle.LINE
    """How contacts are listed"""

    skills: SkillsStyle = SkillsStyle.INLINE
    """How skills are listed"""

    photo_ring: bool = False
    """A ring around the photo"""


class TemplateSpec(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: TemplateId
    """Such as sidebar-band"""

    name: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    """Shown in the template picker"""

    description: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    """One line for the template picker"""

    kinds: list[DocumentKind] = Field(min_length=1)
    """Document kinds it lays out"""

    body_font: Font
    """Font of body text"""

    heading_font: Font
    """Font of the name and section titles"""

    accent: Colour
    """Colour of titles, rules and fills"""

    regions: dict[Region, RegionSpec] = Field(min_length=1)
    """The regions it has"""

    home: dict[BlockKind | Literal["default"], Region]
    """Region each block kind goes to unless the user places it; default for the rest"""

    photo: PhotoSpot = PhotoSpot.TOP
    """Where the photo sits in its region"""

    @model_validator(mode="after")
    def _regions_fit(self) -> Self:
        """Rejects overlapping regions, and a home the template lacks"""
        cells = [
            (row, column)
            for area in (spec.area for spec in self.regions.values())
            for row in range(area.row, area.row + area.rows)
            for column in range(area.column, area.column + area.span)
        ]
        if len(cells) != len(set(cells)):
            raise ValueError(f"regions of {self.id} overlap")
        if "default" not in self.home:
            raise ValueError(f"home of {self.id} has no default")
        if missing := set(self.home.values()) - set(self.regions):
            raise ValueError(f"home of {self.id} names missing regions: {missing}")
        return self
