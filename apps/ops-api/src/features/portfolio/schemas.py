from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.features.portfolio.enums import MediaType
from src.features.profile.schemas import ProfileLink
from src.features.profile.types import EntryEnd, YearMonth

ChangeKind = Literal["about", "skill", "project"]
"""Which part of the site a change is in"""

ChangeType = Literal["added", "changed", "removed"]
"""How the draft differs from the live release"""


class About(BaseModel):
    name: str
    """Full name"""

    headline: str
    """One line under the name"""

    summary: str
    """A short paragraph about the user"""

    location: str
    """Where the user lives"""

    links: list[ProfileLink]
    """Up to three labelled links, such as LinkedIn"""


class SiteSkill(BaseModel):
    id: UUID
    """The skill's id in the profile"""

    name: str
    """The skill or spoken language"""

    group: str
    """Heading it sits under"""


class SiteProject(BaseModel):
    id: UUID
    """The project's id in the profile"""

    title: str
    """Project name"""

    organisation: str
    """Who the project was for"""

    start: YearMonth | None
    """First month"""

    end: EntryEnd | None
    """Last month, or present"""

    summary: str
    """The project's tagline"""

    highlights: list[str]
    """What the user achieved, one sentence each"""

    link: str | None = None
    """Where the project can be seen live"""

    code_link: str | None = None
    """Where the project's code is"""

    tools: list[str] = []
    """Languages, frameworks and tools the project used"""

    image: str | None = None
    """The cover's URL on the site's host, as /sites/<user_id>/media/<sha256>.png"""

    video: str | None = None
    """The video's URL on the site's host, as /sites/<user_id>/media/<sha256>.mp4"""


class Snapshot(BaseModel):
    about: About
    """Who the user is, without contact details"""

    skills: list[SiteSkill]
    """Every skill by group, then name"""

    projects: list[SiteProject]
    """Projects turned on for the site, latest first"""


class Site(Snapshot):
    """sites/<user_id>/release/current.json, which the user's portfolio site reads"""

    number: int
    """The live release's number"""

    published_at: datetime
    """When the live release was published"""


class ReleaseRead(BaseModel):
    id: UUID
    """The release's id"""

    number: int
    """Counts up from 1"""

    published_at: datetime
    """When it was published"""

    live: bool
    """Whether the site serves it"""


class Change(BaseModel):
    kind: ChangeKind
    """Which part of the site"""

    id: UUID | None
    """The skill or project's id; None for about"""

    name: str
    """The skill's name, the project's title, or the user's name"""

    change: ChangeType
    """Added, changed or removed since the live release"""


class DraftRead(BaseModel):
    site_url: str | None
    """Where the site is served; None when there is no site"""

    number: int
    """The number publishing the draft would take"""

    changes: list[Change]
    """What publishing would change on the site; everything is added before the
    first release"""


class Upload(BaseModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    """Hex SHA-256 of the file, worked out in the browser"""

    media_type: MediaType
    """The file's type"""

    size: int = Field(gt=0)
    """Bytes"""

    filename: str = Field(default="", max_length=255)
    """The file's name on the user's computer"""

    @model_validator(mode="after")
    def _within_limit(self) -> Self:
        """Reject a file larger than its type allows"""
        if self.size > self.media_type.max_bytes:
            raise ValueError(self.media_type.too_large)
        return self


class AssetProject(BaseModel):
    id: UUID
    """The project's id in the profile"""

    title: str
    """Project name"""


class AssetRead(BaseModel):
    id: UUID
    """The file's id"""

    sha256: str
    """Hex SHA-256 of the file"""

    media_type: MediaType
    """The file's type"""

    size: int
    """Bytes"""

    filename: str
    """The name it was uploaded with"""

    created_at: datetime
    """When it was uploaded"""

    url: str
    """A short-lived URL to preview the file from"""

    projects: list[AssetProject]
    """The projects showing the file"""


class MediaChoice(BaseModel):
    asset_id: UUID | None
    """The file the project shows; None shows none"""


__all__ = [
    "About",
    "AssetProject",
    "AssetRead",
    "Change",
    "DraftRead",
    "MediaChoice",
    "ReleaseRead",
    "Site",
    "SiteProject",
    "SiteSkill",
    "Snapshot",
    "Upload",
]
