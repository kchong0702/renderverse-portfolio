from pydantic import BaseModel, ConfigDict


class ThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    summary: str | None
    """What the thread said before the messages the agent still sees; None before
    the first summary"""


class SummaryEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    summary: str
    """The summary the user wrote in place of the agent's"""
