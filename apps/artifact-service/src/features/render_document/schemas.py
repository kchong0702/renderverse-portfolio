from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated

from document_schema import (
    ContactKind,
    DataFieldPath,
    Document,
    Id,
    RenderReport,
    SectionKind,
    Sha256,
    Value,
)
from pydantic import (
    Base64Bytes,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: Document
    """The document to render"""

    assets_data: dict[Sha256, Base64Bytes] = Field(default_factory=dict)
    """Bytes of every asset in the document, keyed by their sha256"""

    @model_validator(mode="after")
    def _bytes_match_assets(self) -> RenderRequest:
        for sha, data in self.assets_data.items():
            if sha not in self.document.assets:
                raise ValueError(f"asset bytes {sha} name no document asset")
            if sha256(data).hexdigest() != sha:
                raise ValueError(f"asset bytes do not hash to {sha}")
        for sha in self.document.assets:
            if sha not in self.assets_data:
                raise ValueError(f"asset {sha} has no bytes")
        return self


class RenderResponse(BaseModel):
    html: str
    """Self-contained page the preview shows"""

    pdf: Annotated[
        bytes,
        PlainSerializer(lambda data: base64.b64encode(data).decode(), return_type=str),
    ]
    """The page printed to PDF, base64 in JSON"""

    report: RenderReport
    """Measurements of the render"""


class ViewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)


class ViewValue(Value):
    path: DataFieldPath
    """Where this Value lives in the content, for the element's data-field"""


class ViewContact(ViewModel):
    id: Id
    """Stable key among the header's contacts"""

    kind: ContactKind
    """What the contact value is"""

    value: ViewValue
    """The contact value as written"""


class ViewHeader(ViewModel):
    name: ViewValue
    """Full name"""

    headline: ViewValue | None
    """Title line under the name"""

    contact: list[ViewContact]
    """Contact details in display order"""

    photo: Sha256 | None
    """Sha256 of the profile photo, used as src="asset:{{header.photo}}" in the template"""


class ViewBullet(ViewModel):
    id: Id
    """Stable key among the item's bullets"""

    text: ViewValue
    """Bullet text"""


class ViewTag(ViewModel):
    id: Id
    """Stable key among its sibling tags"""

    text: ViewValue
    """Tag text, such as a skill name"""


class ViewDetail(ViewModel):
    id: Id
    """Stable key among the item's details"""

    label: str
    """Static label, such as GPA"""

    value: ViewValue
    """Value shown next to the label"""


class ViewLink(ViewModel):
    id: Id
    """Stable key among the item's links"""

    url: ViewValue
    """Absolute http or https address, for href"""

    label: ViewValue | None
    """Text shown instead of the address"""


class ViewItem(ViewModel):
    id: Id
    """Stable key among the section's items"""

    title: ViewValue | None
    """Role, degree or project name"""

    organization: ViewValue | None
    """Employer, school or issuer"""

    location: ViewValue | None
    """Where the entry took place"""

    period: ViewValue | None
    """Date range as written"""

    description: ViewValue | None
    """Paragraph describing the entry"""

    details: list[ViewDetail]
    """Labelled facts about the entry"""

    bullets: list[ViewBullet]
    """Bullet points in display order"""

    tags: list[ViewTag]
    """Short labels in display order, such as a skill group or a tech stack"""

    links: list[ViewLink]
    """Related addresses in display order"""


class ViewSection(ViewModel):
    id: Id
    """Stable key among the document's sections"""

    kind: SectionKind
    """What the section holds"""

    heading: ViewValue | None
    """Heading kept exactly as written"""

    text: ViewValue | None
    """Paragraph text for paragraph sections"""

    items: list[ViewItem]
    """Entries in display order"""

    tags: list[ViewTag]
    """Short labels in display order"""

    is_summary: bool
    """True for a summary section"""

    is_experience: bool
    """True for an experience section"""

    is_education: bool
    """True for an education section"""

    is_skills: bool
    """True for a skills section"""

    is_projects: bool
    """True for a projects section"""

    is_languages: bool
    """True for a languages section"""

    is_certifications: bool
    """True for a certifications section"""

    is_awards: bool
    """True for an awards section"""

    is_references: bool
    """True for a references section"""

    is_custom: bool
    """True for a custom section"""


class ContentView(ViewModel):
    header: ViewHeader
    """Name, headline and contact details"""

    sections: list[ViewSection]
    """Visible sections in display order"""


@dataclass(frozen=True)
class View:
    content: ContentView
    """What fills the template: the content without hidden sections."""

    value_paths: list[DataFieldPath]
    """The correspond traverse path for each items in content view
    
    e.g:
    "header/name",
    "sections/exp/heading",
    "sections/exp/items/it_1/title"
    """


@dataclass(frozen=True)
class RenderedHtml:
    html: str
    """Self-contained page: styles, fonts and images are all inline"""

    value_paths: list[DataFieldPath]
    """Path of every Value the template is expected to show"""

    content_width_px: float
    """Width inside the left and right page margins, the width the page lays
    out at"""

    margin_top_px: float
    """Top page margin"""

    margin_bottom_px: float
    """Bottom page margin"""


@dataclass(frozen=True)
class Measurement:
    pdf: bytes
    """The page printed by Chromium"""

    report: RenderReport
    """What the render looks like, for the harness check guard to judge"""
