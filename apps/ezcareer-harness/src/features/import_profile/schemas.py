from typing import Literal

from langchain_core.messages import AnyMessage
from pydantic import BaseModel, ConfigDict, Field

from src.features.import_profile.enums import EntryKind
from src.shared.profile.types import YearMonth


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

    url: str
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

    start: YearMonth | None = None
    """First month"""

    end: YearMonth | Literal["present"] | None = None
    """Last month, or present"""

    summary: str = ""
    """One line about it, from the description"""

    highlights: list[str] = Field(default_factory=list)
    """What the user achieved, one sentence each, from the description"""

    link: str | None = None
    """Where a project can be seen live"""

    code_link: str | None = None
    """Where a project's code is"""

    tools: list[str] = Field(default_factory=list)
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
