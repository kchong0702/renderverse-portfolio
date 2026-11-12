from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, JsonType, PydanticJson, TextArray
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.profile.enums import ChangeKind, EntryKind, ImportSource
from src.features.profile.schemas import (
    ImportedEntry,
    NetworkingDescription,
    NetworkingText,
    ProfileLink,
)
from src.features.profile.types import ChangeField, FieldValue


class Profile(AuditMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("jsonb_array_length(links) <= 3", name="links").ddl_if(
            dialect="postgresql"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    """Whose profile; one row per user, created empty on first read"""

    name: Mapped[str] = mapped_column(String(200), default="")
    """Full name as it goes on a résumé"""

    headline: Mapped[str] = mapped_column(String(200), default="")
    """One line under the name, such as Senior Software Engineer"""

    location: Mapped[str] = mapped_column(String(200), default="")
    """Where the user lives, such as Kuala Lumpur, Malaysia"""

    email: Mapped[str] = mapped_column(String(320), default="")
    """Contact email for documents"""

    phone: Mapped[str] = mapped_column(String(50), default="")
    """Contact phone for documents"""

    links: Mapped[list[ProfileLink]] = mapped_column(
        PydanticJson(TypeAdapter(list[ProfileLink])), default=list
    )
    """Up to three labelled links, such as LinkedIn"""

    summary: Mapped[str] = mapped_column(Text(), default="")
    """A short paragraph about the user"""


class Networking(AuditMixin, Base):
    __tablename__ = "networking_copies"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    """Whose copy; one row per user, created empty on first read"""

    profession: Mapped[str] = mapped_column(String(200), default="")
    """The profession the copy is written for; empty until copy is first kept"""

    headline: Mapped[NetworkingText | None] = mapped_column(
        PydanticJson(TypeAdapter(NetworkingText)), default=None
    )
    """One line under the name; None until written"""

    summary: Mapped[NetworkingText | None] = mapped_column(
        PydanticJson(TypeAdapter(NetworkingText)), default=None
    )
    """The About paragraph; None until written"""

    descriptions: Mapped[list[NetworkingDescription]] = mapped_column(
        PydanticJson(TypeAdapter(list[NetworkingDescription])), default=list
    )
    """A description for each role and project"""

    written_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When copy was last kept; None until then"""


class ProfileEntry(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "profile_entries"

    kind: Mapped[EntryKind] = mapped_column(EnumString(EntryKind))
    """Role, education or project"""

    title: Mapped[str] = mapped_column(String(200))
    """Job title, degree or project name"""

    organisation: Mapped[str] = mapped_column(String(200), default="")
    """Employer, school, or who the project was for"""

    location: Mapped[str] = mapped_column(String(200), default="")
    """Where it took place"""

    start: Mapped[str | None] = mapped_column(String(7), default=None)
    """First month as YYYY-MM"""

    end: Mapped[str | None] = mapped_column(String(7), default=None)
    """Last month as YYYY-MM, or present"""

    summary: Mapped[str] = mapped_column(Text(), default="")
    """One line about it; a project's tagline"""

    highlights: Mapped[list[str]] = mapped_column(TextArray, default=list)
    """What the user achieved, one sentence each"""

    link: Mapped[str | None] = mapped_column(String(500), default=None)
    """Where a project can be seen live; only projects use it"""

    code_link: Mapped[str | None] = mapped_column(String(500), default=None)
    """Where a project's code is; only projects use it"""

    tools: Mapped[list[str]] = mapped_column(TextArray, default=list)
    """Languages, frameworks and tools a project used; only projects use it"""

    archived: Mapped[bool] = mapped_column(default=False)
    """Kept but left out of what the agents see"""

    on_site: Mapped[bool] = mapped_column(default=False, server_default=false())
    """Shown on the portfolio site from the next release; only projects use it"""

    image_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"), default=None)
    """The project's cover image on the portfolio site"""

    video_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"), default=None)
    """The video the portfolio site plays for the project"""


class ProfileSkill(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "profile_skills"

    name: Mapped[str] = mapped_column(String(100))
    """The skill or spoken language, such as Python or Malay"""

    group: Mapped[str] = mapped_column(String(100), default="")
    """Heading it sits under, such as Platform or Spoken languages"""

    archived: Mapped[bool] = mapped_column(default=False)
    """Kept but left out of what the agents see"""


class ProfileImport(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "profile_imports"

    filename: Mapped[str] = mapped_column(String(255))
    """Name of the uploaded file"""

    media_type: Mapped[str] = mapped_column(String(100))
    """PDF, Word or zip"""

    size: Mapped[int] = mapped_column()
    """Bytes in the file"""

    digest: Mapped[str] = mapped_column(String(64))
    """Sha256 of the file"""

    source: Mapped[ImportSource] = mapped_column(EnumString(ImportSource))
    """Whether it was uploaded on the Data page or in Documents"""

    added: Mapped[int] = mapped_column(default=0)
    """Entries, skills, links and empty fields it filled in"""

    conflicts: Mapped[int] = mapped_column(default=0)
    """Fields and matches it left for the user to settle"""

    matched: Mapped[int] = mapped_column(default=0)
    """Entries and skills it found already there"""


class ProfileChange(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "profile_changes"

    import_id: Mapped[UUID] = mapped_column(
        ForeignKey("profile_imports.id", ondelete="CASCADE")
    )
    """The import it came from last; a newer import takes it over"""

    kind: Mapped[ChangeKind] = mapped_column(EnumString(ChangeKind))
    """A differing field or an unsure match"""

    entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("profile_entries.id", ondelete="CASCADE"), default=None
    )
    """The entry it would change or may match; None for the profile's details"""

    field: Mapped[ChangeField | None] = mapped_column(String(20), default=None)
    """Which field differs; None for a match"""

    current: Mapped[FieldValue] = mapped_column(JsonType, default=None)
    """The field's value when the import ran"""

    conflict: Mapped[FieldValue] = mapped_column(JsonType, default=None)
    """The import's value for the field"""

    entry: Mapped[ImportedEntry | None] = mapped_column(
        PydanticJson(TypeAdapter(ImportedEntry)), default=None
    )
    """What the import brought for a match; None for a field"""


__all__ = [
    "Networking",
    "Profile",
    "ProfileChange",
    "ProfileEntry",
    "ProfileImport",
    "ProfileSkill",
]
