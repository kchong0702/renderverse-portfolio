from document_schema.types import Id
from pydantic import BaseModel, ConfigDict


class ProfileFact(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Key the agent cites as fact:<id>"""

    text: str
    """The fact as the user stated it"""
