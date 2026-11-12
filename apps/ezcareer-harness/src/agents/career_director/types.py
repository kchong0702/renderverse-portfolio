from typing import Annotated, Literal

from document_schema import DocumentKind
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class DocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """What edit_document takes to work on the document"""

    title: str
    """The name the user gave the document"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    master: bool
    """Whether it is the user's master document of its kind"""

    updated_at: str
    """When the user last changed it"""


class FoundDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    documents: list[DocumentSummary]
    """The documents that match, best match first"""


class AboutEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["about"]
    """Sets one field about the user"""

    field: Literal["name", "headline", "location", "email", "phone", "summary"]
    """The field to set"""

    value: str
    """The field's new value"""


class EntryEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["entry"]
    """Sets one field of a role, education or project the profile has"""

    fact: str = Field(pattern=r"^(role|education|project)-.+$")
    """The entry's fact id, such as role-<uuid>, as read_profile_facts lists it"""

    field: Literal[
        "title",
        "organisation",
        "location",
        "start",
        "end",
        "summary",
        "highlights",
        "link",
        "code_link",
        "tools",
    ]
    """The field to set"""

    value: str | list[str] | None
    """The field's new value: a list for highlights and tools, null to clear"""


class NewEntryFields(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["role", "education", "project"]
    """What the entry is"""

    title: str
    """The job title, degree or project name"""

    organisation: str = ""
    """The employer or school"""

    location: str = ""
    """Where it was"""

    start: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2})?$")
    """When it started, as YYYY or YYYY-MM"""

    end: str | None = Field(default=None, pattern=r"^(\d{4}(-\d{2})?|present)$")
    """When it ended, as YYYY or YYYY-MM, or present"""

    summary: str = ""
    """A sentence or two about it"""

    highlights: list[str] = []
    """What the user achieved, one line each"""

    link: str | None = None
    """A link to it, such as a project's live site"""

    code_link: str | None = None
    """A project's source code link"""

    tools: list[str] = []
    """The tools and technologies used"""


class NewEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["new_entry"]
    """Adds a role, education or project"""

    entry: NewEntryFields
    """The entry to add"""


class NewSkill(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["new_skill"]
    """Adds a skill"""

    name: str
    """The skill's name"""

    group: str = ""
    """The group it is listed under, such as Languages"""


class NewLink(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["new_link"]
    """Adds a link to the profile, which holds at most 3"""

    label: str = Field(max_length=40)
    """What the link is, such as GitHub"""

    url: str
    """Where the link goes"""


ProfileEdit = Annotated[
    AboutEdit | EntryEdit | NewEntry | NewSkill | NewLink, Field(discriminator="kind")
]


class ProfileSyncPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    edits: list[ProfileEdit]
    """The edits that would bring the profile in line with the document"""


class ProfileUpdated(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    saved: int
    """How many edits were saved"""


class JobRunQueued(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """The queued run's id"""

    run_after: AwareDatetime
    """The earliest a worker may start it"""
