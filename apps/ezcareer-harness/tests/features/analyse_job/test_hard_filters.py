from datetime import date

from src.features.analyse_job.filters import experience_years, hard_filters
from src.features.analyse_job.schemas import PostingTerms
from src.shared.profile import Preferences, Profile, ProfileFact

TODAY = date(2026, 11, 7)
FACTS = [
    ProfileFact(id="acme", text="Engineer at Acme", start="2019-01", end="2022-12"),
    ProfileFact(id="side", text="Freelance work", start="2022-07", end="2023-06"),
    ProfileFact(id="globex", text="Engineer at Globex", start="2024-01", end="present"),
    ProfileFact(id="python", text="Knows Python"),
]
PREFERENCES = Preferences(
    work_modes=["remote", "hybrid"],
    countries=["GB"],
    authorised_countries=["GB", "IE"],
    min_salary={"amount": 70000, "currency": "GBP", "period": "year"},
)


def _filters(terms: dict, preferences: Preferences = PREFERENCES):
    results = hard_filters(
        PostingTerms.model_validate(terms),
        Profile(facts=FACTS, preferences=preferences),
        TODAY,
    )
    return [(f.kind.value, f.passed, f.line_ids) for f in results]


def test_counts_overlapping_spans_once_and_present_as_today():
    # 2019-01..2023-06 is 54 months, 2024-01..2026-11 is 35
    assert experience_years(FACTS, TODAY) == 89 / 12


def test_passes_terms_the_profile_meets():
    assert _filters(
        {
            "min_years": {"value": 7, "line_ids": [3]},
            "work_mode": {"value": "remote", "line_ids": [4]},
            "countries": {"value": ["GB", "DE"], "line_ids": [4]},
            "authorisation_countries": {"value": ["GB"], "line_ids": [9]},
            "salary": {
                "value": {"amount": 85000, "currency": "GBP", "period": "year"},
                "line_ids": [5],
            },
        }
    ) == [
        ("years", True, [3]),
        ("work_mode", True, [4]),
        ("location", True, [4]),
        ("work_authorisation", True, [9]),
        ("salary", True, [5]),
    ]


def test_fails_terms_the_profile_misses():
    assert _filters(
        {
            "min_years": {"value": 8, "line_ids": [3]},
            "work_mode": {"value": "onsite", "line_ids": [4]},
            "countries": {"value": ["US"], "line_ids": [4]},
            "authorisation_countries": {"value": ["US"], "line_ids": [9]},
            "salary": {
                "value": {"amount": 60000, "currency": "GBP", "period": "year"},
                "line_ids": [5],
            },
        }
    ) == [
        ("years", False, [3]),
        ("work_mode", False, [4]),
        ("location", False, [4]),
        ("work_authorisation", False, [9]),
        ("salary", False, [5]),
    ]


def test_skips_terms_the_posting_or_user_leaves_open():
    assert _filters({}) == []
    assert (
        _filters(
            {
                "work_mode": {"value": "onsite", "line_ids": [4]},
                "countries": {"value": ["US"], "line_ids": [4]},
            },
            Preferences(),
        )
        == []
    )
    assert (
        _filters(
            {
                "salary": {
                    "value": {"amount": 40, "currency": "GBP", "period": "hour"},
                    "line_ids": [5],
                }
            }
        )
        == []
    )
