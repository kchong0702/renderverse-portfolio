from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from document_schema.assets import Sha256
from document_schema.base import SchemaModel
from document_schema.value import Id, Value

_HTTP_URL = re.compile(r"^https?://[^\s\"'<>]+$")


def _require_unique(ids: Iterable[str], where: str) -> None:
    seen: set[str] = set()
    for id_ in ids:
        if id_ in seen:
            raise ValueError(f"duplicate id {id_!r} in {where}")
        seen.add(id_)


class ContactKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    LOCATION = "location"
    OTHER = "other"


class SectionKind(StrEnum):
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    LANGUAGES = "languages"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    REFERENCES = "references"
    CUSTOM = "custom"


class Contact(SchemaModel):
    id: Id
    """Stable key among the header's contacts"""

    kind: ContactKind
    """What the contact value is"""

    value: Value
    """The contact value as written"""


class Header(SchemaModel):
    name: Value
    """Full name"""

    headline: Value | None = None
    """Title line under the name"""

    contact: list[Contact] = Field(default_factory=list)
    """Contact details in display order"""

    photo: Sha256 | None = None
    """Sha256 of the profile photo in the document's assets, changed only by the user"""


class Bullet(SchemaModel):
    id: Id
    """Stable key among the item's bullets"""

    text: Value
    """Bullet text"""


class Tag(SchemaModel):
    id: Id
    """Stable key among its sibling tags"""

    text: Value
    """Tag text, such as a skill name"""


class Detail(SchemaModel):
    id: Id
    """Stable key among the item's details"""

    label: str
    """Static label, such as GPA"""

    value: Value
    """Value shown next to the label"""


class Link(SchemaModel):
    id: Id
    """Stable key among the item's links"""

    url: Value
    """Absolute http or https address, such as a repository or a live demo"""

    label: Value | None = None
    """Text shown instead of the address, such as GitHub"""

    @field_validator("url")
    @classmethod
    def _url_is_http(cls, url: Value) -> Value:
        if not _HTTP_URL.match(url.text):
            raise ValueError(
                f"link url {url.text!r} must be an absolute http(s) address"
            )
        return url


class Item(SchemaModel):
    id: Id
    """Stable key among the section's items"""

    title: Value | None = None
    """Role, degree or project name"""

    organization: Value | None = None
    """Employer, school or issuer"""

    location: Value | None = None
    """Where the entry took place"""

    period: Value | None = None
    """Date range as written"""

    description: Value | None = None
    """Paragraph describing the entry"""

    details: list[Detail] = Field(default_factory=list)
    """Labelled facts about the entry"""

    bullets: list[Bullet] = Field(default_factory=list)
    """Bullet points in display order"""

    tags: list[Tag] = Field(default_factory=list)
    """Short labels in display order, such as a skill group or a tech stack"""

    links: list[Link] = Field(default_factory=list)
    """Related addresses in display order"""


class Section(SchemaModel):
    id: Id
    """Stable key among the document's sections"""

    kind: SectionKind
    """What the section holds"""

    heading: Value | None = None
    """Heading kept exactly as written, such as EMPLOYMENT HISTORY

    None for headingless blocks like cover letter paragraphs
    """

    text: Value | None = None
    """Paragraph text for paragraph sections"""

    items: list[Item] = Field(default_factory=list)
    """Entries in display order"""

    tags: list[Tag] = Field(default_factory=list)
    """Short labels in display order"""


class Content(SchemaModel):
    header: Header
    """Name, headline and contact details"""

    sections: list[Section] = Field(default_factory=list)
    """Sections in display order"""

    @model_validator(mode="after")
    def _ids_unique_among_siblings(self) -> Content:
        _require_unique((c.id for c in self.header.contact), "header/contact")
        _require_unique((s.id for s in self.sections), "sections")
        for section in self.sections:
            base = f"sections/{section.id}"
            _require_unique((i.id for i in section.items), f"{base}/items")
            _require_unique((t.id for t in section.tags), f"{base}/tags")
            for item in section.items:
                item_base = f"{base}/items/{item.id}"
                _require_unique((d.id for d in item.details), f"{item_base}/details")
                _require_unique((b.id for b in item.bullets), f"{item_base}/bullets")
                _require_unique((t.id for t in item.tags), f"{item_base}/tags")
                _require_unique((lk.id for lk in item.links), f"{item_base}/links")
        return self
