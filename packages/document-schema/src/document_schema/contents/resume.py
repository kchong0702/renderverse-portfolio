from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from document_schema.blocks.contacts import Contacts
from document_schema.blocks.photo import Photo
from document_schema.blocks.profile import Profile
from document_schema.sections.awards import Awards
from document_schema.sections.certifications import Certifications
from document_schema.sections.custom import Custom
from document_schema.sections.education import Education
from document_schema.sections.experience import Experience
from document_schema.sections.languages import Languages
from document_schema.sections.projects import Projects
from document_schema.sections.publications import Publications
from document_schema.sections.skills import Skills
from document_schema.sections.summary import Summary
from document_schema.types import require_unique_ids

AnyBlock = Annotated[
    Profile
    | Photo
    | Contacts
    | Summary
    | Experience
    | Education
    | Projects
    | Skills
    | Languages
    | Certifications
    | Awards
    | Publications
    | Custom,
    Field(discriminator="kind"),
]


class ResumeContent(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    blocks: list[AnyBlock]
    """Every block, in reading order"""

    @model_validator(mode="after")
    def _blocks_valid(self) -> Self:
        """Rejects a résumé without exactly one profile, or with repeats"""
        require_unique_ids(self.blocks, "blocks")
        kinds = [block.kind for block in self.blocks]
        if kinds.count("profile") != 1:
            raise ValueError("a résumé has exactly one profile")
        for kind in ("photo", "contacts", "summary"):
            if kinds.count(kind) > 1:
                raise ValueError(f"a résumé has at most one {kind}")
        return self
