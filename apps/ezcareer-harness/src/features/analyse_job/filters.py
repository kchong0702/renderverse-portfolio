from collections.abc import Collection
from datetime import date

from src.features.analyse_job.enums import FilterKind
from src.features.analyse_job.schemas import HardFilter, PostingTerms
from src.shared.models import (
    CountryCode,
    Preferences,
    Profile,
    ProfileFact,
    WorkMode,
)


def _month(year_month: str) -> int:
    """Months since year 0 for a YYYY-MM string"""
    year, month = year_month.split("-")
    return int(year) * 12 + int(month) - 1


def experience_years(facts: list[ProfileFact], today: date) -> float:
    """Years covered by the facts' spans, counting overlapping months once"""
    months: set[int] = set()
    for fact in facts:
        if fact.start is None:
            continue
        end = today.strftime("%Y-%m") if fact.end == "present" else fact.end
        months.update(range(_month(fact.start), _month(end or fact.start) + 1))
    return len(months) / 12


def work_mode_fits(modes: Collection[WorkMode], preferences: Preferences) -> bool:
    """Whether the job can be done in a work mode the user accepts;
    true when the user accepts any"""
    return not preferences.work_modes or bool(set(modes) & set(preferences.work_modes))


def countries_fit(countries: Collection[CountryCode], preferences: Preferences) -> bool:
    """Whether the job is in a country the user wants to work in;
    true when the user accepts any"""
    return not preferences.countries or bool(
        set(countries) & set(preferences.countries)
    )


def hard_filters(
    terms: PostingTerms, profile: Profile, today: date
) -> list[HardFilter]:
    """Compare each term the posting states with the profile and preferences.
    Skips a term the user has no preference for."""
    preferences = profile.preferences
    filters: list[HardFilter] = []
    if terms.min_years:
        filters.append(
            HardFilter(
                kind=FilterKind.YEARS,
                passed=experience_years(profile.facts, today) >= terms.min_years.value,
                line_ids=terms.min_years.line_ids,
            )
        )
    if terms.work_mode and preferences.work_modes:
        filters.append(
            HardFilter(
                kind=FilterKind.WORK_MODE,
                passed=work_mode_fits([terms.work_mode.value], preferences),
                line_ids=terms.work_mode.line_ids,
            )
        )
    if terms.countries and preferences.countries:
        filters.append(
            HardFilter(
                kind=FilterKind.LOCATION,
                passed=countries_fit(terms.countries.value, preferences),
                line_ids=terms.countries.line_ids,
            )
        )
    if terms.authorisation_countries and preferences.authorised_countries:
        filters.append(
            HardFilter(
                kind=FilterKind.WORK_AUTHORISATION,
                passed=bool(
                    set(terms.authorisation_countries.value)
                    & set(preferences.authorised_countries)
                ),
                line_ids=terms.authorisation_countries.line_ids,
            )
        )
    salary, minimum = terms.salary, preferences.min_salary
    if (
        salary
        and minimum
        and (salary.value.currency, salary.value.period)
        == (minimum.currency, minimum.period)
    ):
        filters.append(
            HardFilter(
                kind=FilterKind.SALARY,
                passed=salary.value.amount >= minimum.amount,
                line_ids=salary.line_ids,
            )
        )
    return filters
