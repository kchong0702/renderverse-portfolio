from src.features.analyse_job.schemas import (
    JobAnalysis,
    JobRequirements,
    PostingLine,
    Requirement,
)


def _requirement(importance: str, match: str) -> Requirement:
    return Requirement.model_validate(
        {
            "text": "Kubernetes",
            "importance": importance,
            "line_ids": [1],
            "match": match,
            "fact_ids": [] if match == "not_met" else ["fact:k8s"],
            "reason": "-",
        }
    )


def _fit(*requirements: Requirement) -> int:
    analysis = JobAnalysis(
        url="https://jobs.example.com/1",
        lines=[PostingLine(id=1, text="Kubernetes")],
        requirements=list(requirements),
    )
    return analysis.model_dump(mode="json")["fit"]


def test_required_weighs_twice_nice_to_have_and_partly_counts_half():
    assert _fit(_requirement("required", "met")) == 100
    assert _fit(_requirement("required", "not_met")) == 0
    # (2 * 1 + 2 * 0.5 + 1 * 0) / (2 + 2 + 1)
    assert (
        _fit(
            _requirement("required", "met"),
            _requirement("required", "partly"),
            _requirement("nice_to_have", "not_met"),
        )
        == 60
    )
    # (2 * 0 + 1 * 1) / (2 + 1)
    assert (
        _fit(_requirement("required", "not_met"), _requirement("nice_to_have", "met"))
        == 33
    )


def test_the_agent_cannot_write_the_fit():
    assert "fit" not in JobRequirements.model_json_schema()["properties"]
    assert "fit" in JobAnalysis.model_json_schema(mode="serialization")["properties"]
