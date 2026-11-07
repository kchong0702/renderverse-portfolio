from collections.abc import Callable, Mapping

from document_schema import AnyDocument, Changeset
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.features.write_document.checks import check_changeset
from src.shared.checks import CheckError

Check = Callable[[AnyDocument, Changeset, Mapping[str, str]], list[CheckError]]
"""A check on a changeset: the document, the changeset and the citable sources"""

CHECKS: dict[str, Check] = {"changeset": check_changeset}
"""Every check the edit flow can run on a changeset, by name"""


class EditProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[str] = Field(default_factory=list)
    """Checks the validate node runs on each changeset"""

    recursion_limit: int = Field(gt=0)
    """Graph steps before an edit fails; each check round takes two"""

    agent_recursion_limit: int = Field(gt=0)
    """Steps one career-consultant run may take"""

    page_fit_trims: int = Field(ge=0)
    """Bullets page-fit may remove before it hands the changeset over as it is"""

    @field_validator("checks")
    @classmethod
    def _known(cls, checks: list[str]) -> list[str]:
        """Refuses a check the edit flow doesn't have"""
        if unknown := [name for name in checks if name not in CHECKS]:
            raise ValueError(
                f"unknown checks {unknown}; the edit flow has {sorted(CHECKS)}"
            )
        return checks
