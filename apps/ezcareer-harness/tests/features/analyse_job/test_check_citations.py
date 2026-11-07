import pytest

from src.features.analyse_job.checks import check_citations
from src.features.analyse_job.schemas import (
    JobRequirements,
    PostingLine,
    Requirement,
)
from src.shared.models import ProfileFact

LINES = [
    PostingLine(id=1, text="5+ years of Python in production"),
    PostingLine(id=2, text="Strong PostgreSQL skills, including query tuning and"),
    PostingLine(id=3, text="schema migrations"),
    PostingLine(id=4, text="Kubernetes"),
]
FACTS = [
    ProfileFact(id="acme", text="Backend engineer at Acme, Python and FastAPI"),
    ProfileFact(id="pg", text="Tuned PostgreSQL queries for a billing service"),
]


def _requirement(**overrides) -> Requirement:
    fields = {
        "text": "5+ years of Python in production",
        "importance": "required",
        "line_ids": [1],
        "match": "met",
        "fact_ids": ["fact:acme"],
        "reason": "Six years of Python at Acme.",
    }
    return Requirement.model_validate({**fields, **overrides})


def _check(*requirements: Requirement, terms: dict | None = None):
    output = JobRequirements.model_validate(
        {"requirements": list(requirements), "terms": terms or {}}
    )
    return check_citations(output, LINES, FACTS)


def test_passes_cited_verbatim_requirements():
    assert (
        _check(
            _requirement(),
            _requirement(
                text="query tuning and schema migrations",
                line_ids=[2, 3],
                match="partly",
                fact_ids=["fact:pg"],
            ),
            _requirement(
                text="Kubernetes",
                importance="nice_to_have",
                line_ids=[4],
                match="not_met",
                fact_ids=[],
            ),
        )
        == []
    )


@pytest.mark.parametrize(
    ("requirement", "rule"),
    [
        (_requirement(line_ids=[9]), "unknown_line"),
        (_requirement(text="Five years of Python"), "not_verbatim"),
        (_requirement(text="Kubernetes", line_ids=[1]), "not_verbatim"),
        (_requirement(fact_ids=["fact:google"]), "unknown_fact"),
        (_requirement(match="partly", fact_ids=[]), "uncited_match"),
    ],
)
def test_reports_each_broken_citation(requirement: Requirement, rule: str):
    errors = _check(_requirement(), requirement)

    assert [(e.rule, e.at) for e in errors] == [(rule, "requirements[1]")]


def test_reports_terms_citing_missing_lines():
    errors = _check(
        _requirement(),
        terms={
            "min_years": {"value": 5, "line_ids": [1]},
            "work_mode": {"value": "remote", "line_ids": [12]},
        },
    )

    assert [(e.rule, e.at) for e in errors] == [("unknown_line", "terms.work_mode")]
