from pydantic import BaseModel, ConfigDict

from src.shared.checks.enums import CheckRule


class CheckError(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    rule: CheckRule
    """The rule that failed"""

    at: str
    """Where in the agent's output, such as requirements[2]"""

    message: str
    """What is wrong, written for the agent to fix"""
