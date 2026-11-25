from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from document_schema import AnyDocument, DocumentKind
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.shared.extraction.types import Line

ApplicationStage = Literal[
    "draft", "applied", "replied", "interview", "offer", "closed"
]
JobStatus = Literal["picked", "saved", "dismissed"]


class DocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """The document_id handoff_document takes to hand the document to
    career-consultant"""

    title: str
    """The name the user gave the document"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    master: bool
    """Whether it is the user's master document of its kind"""

    updated_at: str
    """When the user last changed it"""


class DocumentContent(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    document: AnyDocument
    """The document as it is now, which career-consultant is handed"""

    pdf_lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""


class FoundDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    documents: list[DocumentSummary]
    """The documents that match, best match first"""

    content: DocumentContent | None
    """The best match's document and PDF lines; None when nothing matches"""


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


class ApplicationStep(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["interview", "follow_up", "take_home", "offer_deadline"]
    """What the step is"""

    title: str
    """What it is, such as Technical interview; empty to go by its kind"""

    starts_at: AwareDatetime | None
    """When it starts; None for a step that only has a due day"""

    due_on: date | None
    """The day it must be done by"""

    format: Literal["video", "phone", "on_site"] | None
    """Whether it is a video call, a phone call or on site"""

    location: str | None
    """Where it happens, such as an address or a meeting link"""


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    company: str
    """Employer applied to"""

    role: str
    """Job title applied for"""

    stage: ApplicationStage
    """Where it stands in the pipeline"""

    applied_on: date | None
    """The day it was sent"""

    fit: int | None
    """The job's fit score; None until the job is analysed"""

    next_step: ApplicationStep | None
    """The soonest open step still ahead; None when there is none"""

    overdue: list[ApplicationStep]
    """Open steps whose due day has passed, oldest first"""


class FoundApplications(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    by_stage: dict[ApplicationStage, int]
    """How many applications of the company asked are at each stage"""

    applications: list[ApplicationSummary]
    """The applications asked for, overdue first, then soonest next step first"""

    timezone: ZoneInfo
    """The user's time zone"""


class SavedJob(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    title: str
    """The job title"""

    company: str
    """The employer"""

    location: str
    """Where the job is"""

    salary: str
    """The pay, as the posting gives it"""

    url: str
    """Where the posting is"""

    posted_at: datetime | None
    """When it was posted, if known"""

    status: JobStatus
    """Picked by the job agent, saved by the user, or dismissed"""

    fit: int | None
    """How well it fits the profile, out of 100; None until it is analysed"""


class FoundSavedJobs(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    by_status: dict[JobStatus, int]
    """How many jobs of the company asked have each status"""

    jobs: list[SavedJob]
    """The jobs asked for, best fit first, unanalysed ones last"""
