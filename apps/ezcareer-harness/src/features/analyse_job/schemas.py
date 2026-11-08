from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field

from src.features.analyse_job.enums import FilterKind, Importance, Match
from src.shared.profile import CountryCode, FactRef, Salary, WorkMode

_WEIGHTS = {Importance.REQUIRED: 2, Importance.NICE_TO_HAVE: 1}
_CREDITS = {Match.MET: 1.0, Match.PARTLY: 0.5, Match.NOT_MET: 0.0}


class PostingLine(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: int
    """Line number, counted from 1"""

    text: str
    """The line's text; untrusted"""


class Requirement(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    text: str
    """The requirement word for word from the posting"""

    importance: Importance
    """Whether the posting requires it or calls it nice to have"""

    line_ids: list[int] = Field(min_length=1)
    """Posting lines the text is taken from, in order"""

    match: Match
    """How well the profile meets it"""

    fact_ids: list[FactRef] = Field(default_factory=list)
    """Profile facts that show the match, as fact:<id>"""

    reason: str
    """Why it is met, partly met or not met, in one sentence"""


class Cited[T](BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    value: T
    """What the posting states"""

    line_ids: list[int] = Field(min_length=1)
    """Posting lines that state it"""


class PostingTerms(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    min_years: Cited[int] | None = None
    """Years of experience asked for overall, not per skill"""

    work_mode: Cited[WorkMode] | None = None
    """Whether the job is onsite, hybrid or remote"""

    countries: Cited[list[CountryCode]] | None = None
    """Countries the job is based in, or open to when remote"""

    authorisation_countries: Cited[list[CountryCode]] | None = None
    """Countries the candidate must already have the right to work in"""

    salary: Cited[Salary] | None = None
    """Top of the stated pay range"""


class HardFilter(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: FilterKind
    """What the filter compares"""

    passed: bool
    """Whether the profile and preferences satisfy the posting"""

    line_ids: list[int]
    """Posting lines that state the term"""


def fit_score(requirements: list[Requirement]) -> int:
    """Percent of the weighted requirements met; partly counts half.
    Required ones weigh twice as much as nice to have."""
    total = sum(_WEIGHTS[r.importance] for r in requirements)
    earned = sum(_WEIGHTS[r.importance] * _CREDITS[r.match] for r in requirements)
    return round(100 * earned / total)


class JobRequirements(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    requirements: list[Requirement] = Field(min_length=1)
    """Every requirement the posting states, mapped to the profile"""

    terms: PostingTerms = Field(default_factory=PostingTerms)
    """Terms the posting states that code checks against the profile"""


class JobAnalysis(JobRequirements):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    url: HttpUrl
    """Where the posting was fetched from"""

    lines: list[PostingLine]
    """The posting's text, so citations can be shown"""

    filters: list[HardFilter]
    """Hard filters computed in code, one per stated term"""

    @computed_field
    @property
    def fit(self) -> int:
        """Fit score from 0 to 100, computed from the requirements"""
        return fit_score(self.requirements)
