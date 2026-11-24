from pydantic import BaseModel, ConfigDict


class ChangesetProposed(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    changeset_id: str
    """The id ops-api saved the proposed changeset under"""
