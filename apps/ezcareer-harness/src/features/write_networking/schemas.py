from typing import Annotated, Literal, Self

from document_schema.types import Id
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.shared.profile import ProfileFact


class Passage(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    text: str
    """Plain text ready to paste, a line per paragraph or • bullet"""

    facts: list[Id] = Field(min_length=1)
    """Ids of the profile facts it rests on, such as role-1"""


class Description(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    fact: Id
    """The id of the role or project fact it describes"""

    text: str
    """Plain text ready to paste, a scope line then • bullets"""

    facts: list[Id] = Field(min_length=1)
    """Ids of the profile facts it rests on, such as role-1"""


class NetworkingCopy(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    headline: Passage | None = None
    """The one line under the user's name; None when not asked for"""

    summary: Passage | None = None
    """The about section; None when not asked for"""

    descriptions: list[Description] = Field(default_factory=list)
    """A description of each role and project asked for"""

    def written(self) -> dict[str, Passage | Description]:
        """Each field written, by headline, summary or the described fact's id"""
        return {
            **({"headline": self.headline} if self.headline else {}),
            **({"summary": self.summary} if self.summary else {}),
            **{description.fact: description for description in self.descriptions},
        }


class WriteNetworkingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    aim: str = ""
    """The jobs the user aims for, in their words"""

    facts: list[ProfileFact]
    """Every profile fact, those switched off for the assistant included"""

    only: Literal["headline", "summary"] | Id | None = None
    """The one field to write: headline, summary or a role or project fact's id;
    None writes them all"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The user's note, if any, then the agent's conversation across check rounds"""

    @model_validator(mode="after")
    def _only_names_a_field(self) -> Self:
        """Rejects an only that isn't headline, summary or a role or project fact"""
        if self.only not in (None, "headline", "summary", *self.described()):
            raise ValueError(
                f"{self.only} is not headline, summary or a role or project"
            )
        return self

    def described(self) -> list[Id]:
        """Ids of the role and project facts, each of which gets a description"""
        return [
            fact.id for fact in self.facts if fact.id.startswith(("role-", "project-"))
        ]

    def fields(self) -> list[str]:
        """What to write: headline, summary and each role and project fact's id, or
        only the one field asked for"""
        if self.only is None:
            return ["headline", "summary", *self.described()]
        return [self.only]
