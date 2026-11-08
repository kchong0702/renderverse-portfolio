from datetime import UTC, datetime

from src.features.analyse_job import PostingLine
from src.features.find_jobs.checks import check_ranked_jobs
from src.features.find_jobs.ranking import matched_jobs
from src.features.find_jobs.schemas import JobPosting, RankedJobs
from src.shared.profile import Preferences, Profile, ProfileFact


def _posting(job_id: str, *lines: str, remote: bool = True) -> JobPosting:
    return JobPosting(
        id=job_id,
        title=f"Engineer {job_id}",
        company="Acme",
        location="London, GB",
        country="GB",
        remote=remote,
        posted_at=datetime(2026, 11, 6, tzinfo=UTC),
        apply_url=f"https://jobs.example.com/{job_id}",
        lines=[PostingLine(id=n, text=t) for n, t in enumerate(lines, start=1)],
    )


POSTINGS = [
    _posting("a", "Python", "Kubernetes"),
    _posting("b", "Terraform"),
    _posting("c", "Go"),
]
FACTS = [ProfileFact(id="py", text="Python at Acme")]
PROFILE = Profile(facts=FACTS)


def _requirement(text: str, line: int, match: str = "met") -> dict:
    return {
        "text": text,
        "importance": "required",
        "line_ids": [line],
        "match": match,
        "fact_ids": [] if match == "not_met" else ["fact:py"],
        "reason": "-",
    }


def _ranked(*jobs: tuple[str, list[dict]]) -> RankedJobs:
    return RankedJobs.model_validate(
        {"jobs": [{"job_id": i, "requirements": r} for i, r in jobs]}
    )


def test_passes_jobs_from_search_with_valid_citations():
    output = _ranked(
        ("a", [_requirement("Python", 1), _requirement("Kubernetes", 2, "not_met")]),
        ("b", [_requirement("Terraform", 1, "not_met")]),
    )

    assert check_ranked_jobs(output, POSTINGS, PROFILE) == []


def test_reports_unknown_and_repeated_jobs_and_bad_citations():
    output = _ranked(
        ("a", [_requirement("Python", 1)]),
        ("invented", [_requirement("Python", 1)]),
        ("a", [_requirement("Python", 1)]),
        ("b", [_requirement("Kubernetes", 1)]),
    )

    errors = check_ranked_jobs(output, POSTINGS, PROFILE)

    assert [(e.rule, e.at) for e in errors] == [
        ("unknown_job", "jobs[1]"),
        ("duplicate_job", "jobs[2]"),
        ("not_verbatim", "jobs[3].requirements[0]"),
    ]


def test_orders_by_fit_and_takes_details_from_search():
    output = _ranked(
        ("c", [_requirement("Go", 1, "not_met")]),
        ("b", [_requirement("Terraform", 1, "partly")]),
        ("a", [_requirement("Python", 1)]),
    )

    ranked = matched_jobs(output, POSTINGS)

    assert [(job.posting.id, job.fit) for job in ranked] == [
        ("a", 100),
        ("b", 50),
        ("c", 0),
    ]
    assert ranked[0].posting == POSTINGS[0]


def test_keeps_the_agents_order_for_equal_fits():
    output = _ranked(
        ("b", [_requirement("Terraform", 1)]),
        ("a", [_requirement("Python", 1)]),
    )

    assert [job.posting.id for job in matched_jobs(output, POSTINGS)] == ["b", "a"]


def test_reports_jobs_that_break_the_users_preferences():
    london_onsite = _posting("london", "Python", remote=False)
    remote_only = Profile(
        facts=FACTS, preferences=Preferences(work_modes=["remote"], countries=["GB"])
    )
    output = _ranked(
        ("london", [_requirement("Python", 1)]), ("a", [_requirement("Python", 1)])
    )

    errors = check_ranked_jobs(output, [london_onsite, *POSTINGS], remote_only)

    assert [(e.rule, e.at) for e in errors] == [("breaks_preferences", "jobs[0]")]
    assert "work_mode" in errors[0].message
