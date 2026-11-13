from __future__ import annotations

from base64 import b64encode
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from document_schema import ResumeDocument
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    model_validator,
)

from src.features.preferences.enums import WorkMode
from src.features.preferences.schemas import Salary
from src.features.preferences.types import CountryCode
from src.features.profile.enums import (
    ChangeChoice,
    ChangeKind,
    EntryKind,
    ImportSource,
)
from src.features.profile.types import (
    ChangeField,
    EntryEnd,
    FactId,
    FieldValue,
    Highlight,
    Link,
    LooseMonth,
    Tool,
    YearMonth,
    clipped,
)


class ProfileLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    """What the link is for, such as LinkedIn or GitHub"""

    url: Link
    """Where it points"""


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_modes: list[WorkMode] = Field(default_factory=list)
    """Work modes the user accepts; empty accepts any"""

    countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user wants to work in; empty accepts any"""

    authorised_countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user may work in without visa sponsorship"""

    min_salary: Salary | None = None
    """Lowest pay the user accepts"""


class ProfileRead(BaseModel):
    name: str
    """Full name as it goes on a résumé"""

    headline: str
    """One line under the name"""

    location: str
    """Where the user lives"""

    email: str
    """Contact email for documents"""

    phone: str
    """Contact phone for documents"""

    links: list[ProfileLink]
    """Up to three labelled links, such as LinkedIn"""

    summary: str
    """A short paragraph about the user"""


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    """New full name; None leaves it unchanged"""

    headline: str | None = Field(default=None, max_length=200)
    """New headline; None leaves it unchanged"""

    location: str | None = Field(default=None, max_length=200)
    """New location; None leaves it unchanged"""

    email: str | None = Field(default=None, max_length=320)
    """New contact email; None leaves it unchanged"""

    phone: str | None = Field(default=None, max_length=50)
    """New contact phone; None leaves it unchanged"""

    links: list[ProfileLink] | None = Field(default=None, max_length=3)
    """Replaces every link, at most three; None leaves them unchanged"""

    summary: str | None = None
    """New summary; None leaves it unchanged"""


class EntryWrite(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    """Job title, degree or project name"""

    organisation: str = Field(default="", max_length=200)
    """Employer, school, or who the project was for"""

    location: str = Field(default="", max_length=200)
    """Where it took place"""

    start: YearMonth | None = None
    """First month"""

    end: EntryEnd | None = None
    """Last month, or present; not before start"""

    summary: str = ""
    """One line about it; a project's tagline"""

    highlights: list[Highlight] = Field(default_factory=list)
    """What the user achieved, one sentence each"""

    link: Link | None = None
    """Where a project can be seen live; only projects use it"""

    code_link: Link | None = None
    """Where a project's code is; only projects use it"""

    tools: list[Tool] = Field(default_factory=list, max_length=20)
    """Languages, frameworks and tools a project used; only projects use it"""

    archived: bool = False
    """Kept but left out of what the agents see"""

    on_site: bool = False
    """Shown on the portfolio site from the next release; only projects use it"""

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Self:
        """Reject an end month earlier than the start month"""
        if self.start and self.end and self.end != "present" and self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class EntryCreate(EntryWrite):
    kind: EntryKind
    """Role, education or project; fixed once created"""


class EntryRead(EntryCreate):
    id: UUID
    """The entry's id"""

    image_id: UUID | None = None
    """A project's cover image on the site, set through the portfolio"""

    video_id: UUID | None = None
    """A project's video on the site, set through the portfolio"""


class SkillWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    """The skill or spoken language, such as Python or Malay"""

    group: str = Field(default="", max_length=100)
    """Heading it sits under, such as Platform or Spoken languages"""

    archived: bool = False
    """Kept but left out of what the agents see"""


class SkillRead(SkillWrite):
    id: UUID
    """The skill's id"""


class ProfileFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: FactId
    """Key the agents cite as fact:<id>"""

    text: str
    """The fact in the user's words"""

    start: YearMonth | None = None
    """When a job began; years of experience count these spans"""

    end: EntryEnd | None = None
    """When the job ended, or present"""


class AgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[ProfileFact]
    """What the user has done and knows, without archived items"""

    preferences: Preferences
    """What the user wants from a job"""


class ExportFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    """The file's name in the export, such as Positions.csv"""

    rows: list[dict[str, str]]
    """Each row as column name to value"""


class ProfileExport(BaseModel):
    files: list[ExportFile]
    """The profile, job, education, project and skill files"""

    name: Annotated[str, clipped(200)]
    """Full name from the export's profile; empty when it has none"""

    email: Annotated[str, clipped(320)]
    """The primary email, else the first; empty when it has none"""

    phone: Annotated[str, clipped(50)]
    """The first phone number; empty when it has none"""


class ImportProfileInput(BaseModel):
    files: list[ExportFile]
    """The export's profile, job, education, project and skill files"""


class ResumeFile(BaseModel):
    file: Annotated[
        bytes,
        PlainSerializer(
            lambda file: b64encode(file).decode(), return_type=str, when_used="json"
        ),
    ]
    """The uploaded PDF or Word file, standard base64 in JSON"""


class ImportedResume(BaseModel):
    document: ResumeDocument
    """The draft document made from the file"""


class ImportedAbout(BaseModel):
    name: Annotated[str, clipped(200)] = ""
    """Full name; empty when the import has none"""

    headline: Annotated[str, clipped(200)] = ""
    """One line under the name"""

    location: Annotated[str, clipped(200)] = ""
    """Where the user lives"""

    email: Annotated[str, clipped(320)] = ""
    """Contact email"""

    phone: Annotated[str, clipped(50)] = ""
    """Contact phone"""

    summary: str = ""
    """A short paragraph about the user"""

    links: list[ProfileLink] = Field(default_factory=list)
    """Labelled links, such as LinkedIn"""


class ImportedEntry(BaseModel):
    kind: EntryKind
    """Role, education or project"""

    title: Annotated[str, clipped(200)] = Field(min_length=1)
    """Job title, degree or project name"""

    organisation: Annotated[str, clipped(200)] = ""
    """Employer, school, or who the project was for"""

    location: Annotated[str, clipped(200)] = ""
    """Where it took place"""

    start: LooseMonth | None = None
    """First month, or only its year"""

    end: LooseMonth | Literal["present"] | None = None
    """Last month or only its year, or present"""

    summary: str = ""
    """One line about it"""

    highlights: list[Highlight] = Field(default_factory=list)
    """What the user achieved, one sentence each"""

    link: Link | None = None
    """Where a project can be seen live"""

    code_link: Link | None = None
    """Where a project's code is"""

    tools: list[Annotated[str, StringConstraints(min_length=1), clipped(50)]] = Field(
        default_factory=list, max_length=20
    )
    """Languages, frameworks and tools a project used"""


class ImportedSkill(BaseModel):
    name: Annotated[str, clipped(100)] = Field(min_length=1)
    """The skill or spoken language"""

    group: Annotated[str, clipped(100)] = ""
    """Heading it sits under"""


class ImportedProfile(BaseModel):
    about: ImportedAbout = Field(default_factory=ImportedAbout)
    """The user's details"""

    entries: list[ImportedEntry] = Field(default_factory=list)
    """Roles, education and projects"""

    skills: list[ImportedSkill] = Field(default_factory=list)
    """Skills and spoken languages"""


class ProfileImportRead(BaseModel):
    id: UUID
    """The import's id"""

    filename: str
    """Name of the uploaded file"""

    media_type: str
    """PDF, Word or zip"""

    source: ImportSource
    """Whether it was uploaded on the Data page or in Documents"""

    added: int
    """Entries, skills, links and empty fields it filled in"""

    conflicts: int
    """Fields and matches it left for the user to settle"""

    matched: int
    """Entries and skills it found already there"""

    created_at: datetime
    """When it was imported"""


class FieldChangeRead(BaseModel):
    kind: Literal[ChangeKind.FIELD] = ChangeKind.FIELD
    """A field whose imported value differs from the current one"""

    id: UUID
    """The change's id"""

    import_id: UUID
    """The import it came from last"""

    entry_id: UUID | None
    """The entry it would change; None for the profile's own details"""

    field: ChangeField
    """Which field"""

    current: FieldValue
    """The field's value when the import ran"""

    conflict: FieldValue
    """The import's value"""


class MatchChangeRead(BaseModel):
    kind: Literal[ChangeKind.MATCH] = ChangeKind.MATCH
    """An imported entry that may be one already there"""

    id: UUID
    """The change's id"""

    import_id: UUID
    """The import it came from last"""

    entry_id: UUID
    """The entry it may be"""

    entry: ImportedEntry
    """What the import brought"""


ChangeRead = Annotated[FieldChangeRead | MatchChangeRead, Field(discriminator="kind")]
"""A pending change from an import"""


class ChangeAnswer(BaseModel):
    id: UUID
    """The change answered"""

    choice: ChangeChoice
    """current or conflict for a field; same or different for a match"""


class ChangeAnswers(BaseModel):
    answers: list[ChangeAnswer] = Field(min_length=1)
    """One answer per change settled"""


class NetworkingText(BaseModel):
    text: str
    """Copy to paste into a job portal"""

    facts: list[FactId]
    """The facts it was written from"""


class NetworkingDescription(NetworkingText):
    fact: FactId
    """The role or project it describes"""


class NetworkingCopy(BaseModel):
    headline: NetworkingText | None = None
    """One line under the name; None until written"""

    summary: NetworkingText | None = None
    """The About paragraph; None until written"""

    descriptions: list[NetworkingDescription] = Field(default_factory=list)
    """A description for each role and project"""


class NetworkingRead(NetworkingCopy):
    profession: str
    """The profession the copy is written for"""


class NetworkingWrite(BaseModel):
    profession: str = Field(max_length=200)
    """The profession the copy is written for, such as Senior Backend Engineer"""

    only: Literal["headline", "summary"] | FactId | None = None
    """Rewrite only the headline, summary or one role's or project's description;
    None for all"""


class WriteNetworkingInput(BaseModel):
    profession: str
    """The profession the copy is written for"""

    facts: list[ProfileFact]
    """Every fact, archived ones included"""

    only: str | None
    """headline, summary or a fact id to rewrite only that; None for all"""


__all__ = [
    "AgentProfile",
    "ChangeAnswer",
    "ChangeAnswers",
    "ChangeRead",
    "EntryCreate",
    "EntryRead",
    "EntryWrite",
    "ExportFile",
    "FieldChangeRead",
    "ImportProfileInput",
    "ImportedAbout",
    "ImportedEntry",
    "ImportedProfile",
    "ImportedResume",
    "ImportedSkill",
    "MatchChangeRead",
    "NetworkingCopy",
    "NetworkingDescription",
    "NetworkingRead",
    "NetworkingText",
    "NetworkingWrite",
    "Preferences",
    "ProfileExport",
    "ProfileFact",
    "ProfileImportRead",
    "ProfileLink",
    "ProfileRead",
    "ProfileUpdate",
    "ResumeFile",
    "SkillRead",
    "SkillWrite",
    "WriteNetworkingInput",
]
