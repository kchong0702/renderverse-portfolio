from pydantic import BaseModel, ConfigDict


class CheckError(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    rule: str
    """Name of the rule that failed, such as unknown_line"""

    at: str
    """Where in the agent's output, such as requirements[2]"""

    message: str
    """What is wrong, written for the agent to fix"""
