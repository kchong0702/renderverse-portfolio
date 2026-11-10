from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

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

    links: list[str]
    """Profile and portfolio URLs"""


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


class Snapshot(BaseModel):
    about: About
    """Who the user is, without contact details"""

    skills: list[SiteSkill]
    """Unarchived skills by group, then name"""

    projects: list[SiteProject]
    """Unarchived projects turned on for the site, latest first"""


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


__all__ = [
    "About",
    "Change",
    "DraftRead",
    "ReleaseRead",
    "Site",
    "SiteProject",
    "SiteSkill",
    "Snapshot",
]
