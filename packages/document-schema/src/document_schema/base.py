from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)
