from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.profile.schemas import ImportedEntry, ProfileLink
from src.features.profile.types import FieldValue


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """What the user asks the assistant"""


class AboutEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["about"]
    """Set one of the user's details"""

    field: Literal["name", "headline", "location", "email", "phone", "summary"]
    """Which detail"""

    value: str
    """Its new value"""


class EntryEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["entry"]
    """Set one field of an existing role, education or project"""

    fact: str
    """The entry's fact id, such as role-<uuid>"""

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
    """Which field"""

    value: FieldValue
    """Its new value: text, every line for highlights or tools, or None to clear"""


class NewEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["new_entry"]
    """Add a role, education or project"""

    entry: ImportedEntry
    """The entry to add"""


class NewSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["new_skill"]
    """Add a skill"""

    name: str
    """The skill or spoken language"""

    group: str = ""
    """Heading it sits under"""


class NewLink(ProfileLink):
    kind: Literal["new_link"]
    """Add a labelled link to the user's details"""


ProfileEdit = Annotated[
    AboutEdit | EntryEdit | NewEntry | NewSkill | NewLink, Field(discriminator="kind")
]
"""One change career-director proposes to the user's details"""


class UpdateProfileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edits: list[ProfileEdit] = Field(min_length=1)
    """Every change to make"""

    source: str = ""
    """The title of the document the changes come from; empty when the user asked"""


class ProfileSyncPreview(BaseModel):
    edits: list[ProfileEdit]
    """What syncing would change, saving nothing"""


class ProfileUpdated(BaseModel):
    saved: int
    """How many changes were saved"""


class ApprovalRow(BaseModel):
    edit: ProfileEdit
    """The change"""

    entry: str | None
    """The entry's organisation, else its title; None for any other change"""

    current: FieldValue
    """What the field holds now, read from the database; None for an addition"""


class ProfileApproval(BaseModel):
    status: Literal["profile_approval"] = "profile_approval"
    """The run paused for the user to approve changes to their details"""

    task_id: str
    """The paused task; the decision goes back on it"""

    source: str
    """The title of the document the changes come from; empty when the user asked"""

    rows: list[ApprovalRow]
    """One row per change"""


class ProfileSaved(BaseModel):
    status: Literal["profile_saved"] = "profile_saved"
    """The run saved changes to the user's details"""

    saved: int
    """How many"""


class ProfileDecision(BaseModel):
    approve: bool
    """True saves the changes, False cancels them"""

    message: str | None = Field(default=None, max_length=4000)
    """What the user typed instead of approving; the model gets it as the reason"""


__all__ = [
    "AboutEdit",
    "ApprovalRow",
    "ChatMessage",
    "EntryEdit",
    "NewEntry",
    "NewLink",
    "NewSkill",
    "ProfileApproval",
    "ProfileDecision",
    "ProfileEdit",
    "ProfileSaved",
    "ProfileSyncPreview",
    "ProfileUpdated",
    "UpdateProfileArgs",
]
