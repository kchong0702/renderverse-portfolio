from enum import StrEnum
from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class EntryKind(StrEnum):
    ROLE = "role"
    """A job the user held"""

    EDUCATION = "education"
    """A degree, course or school"""

    PROJECT = "project"
    """Something the user built or led"""


class ExportFile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    name: str
    """The file's name in the export, such as Positions.csv"""

    rows: list[dict[str, str]]
    """The file's rows, each by column header"""


class ImportProfileInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    files: list[ExportFile] = Field(min_length=1)
    """The export's profile files, unpacked"""

    messages: list[AnyMessage] = Field(default_factory=list)
    """The user's note on how to import the export, if any"""


class ImportedLink(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    label: str = Field(min_length=1, max_length=40)
    """What the link is for, such as LinkedIn or Portfolio"""

    url: str = Field(min_length=1)
    """The URL as the export writes it"""


class ImportedAbout(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    headline: str = ""
    """The one line under the user's name"""

    summary: str = ""
    """The paragraph about the user"""

    location: str = ""
    """Where the user lives"""

    links: list[ImportedLink] = Field(default_factory=list, max_length=3)
    """Up to three of the user's own links"""


class ImportedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: EntryKind
    """Role, education or project"""

    title: str = Field(min_length=1)
    """Job title, degree or project name"""

    organisation: str = ""
    """Employer, school, or who the project was for"""

    location: str = ""
    """Where it took place"""

    start: (
        Annotated[str, StringConstraints(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")] | None
    ) = None
    """First month, or only its year when the row gives no month"""

    end: (
        Annotated[str, StringConstraints(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")]
        | Literal["present"]
        | None
    ) = None
    """Last month or only its year, or present"""

    summary: str = ""
    """One line about it, from the description"""

    highlights: list[Annotated[str, StringConstraints(min_length=1)]] = Field(
        default_factory=list
    )
    """What the user achieved, one sentence each, from the description"""

    link: str | None = Field(default=None, min_length=1)
    """Where a project can be seen live"""

    code_link: str | None = Field(default=None, min_length=1)
    """Where a project's code is"""

    tools: list[Annotated[str, StringConstraints(min_length=1)]] = Field(
        default_factory=list, max_length=20
    )
    """Languages, frameworks and tools a project names"""


class ImportedSkill(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    name: str = Field(min_length=1)
    """The skill or spoken language, such as Python or Malay"""

    group: str = ""
    """Heading it sits under, such as Platform or Spoken languages"""


class ProfileImport(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    about: ImportedAbout = Field(default_factory=ImportedAbout)
    """Headline, summary, location and links"""

    entries: list[ImportedEntry] = Field(default_factory=list)
    """Every role, education and project, in the export's order"""

    skills: list[ImportedSkill] = Field(default_factory=list)
    """Every skill, grouped under headings"""
