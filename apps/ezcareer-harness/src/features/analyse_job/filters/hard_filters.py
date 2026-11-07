from datetime import date

from src.features.analyse_job.enums import FilterKind
from src.features.analyse_job.filters.experience import experience_years
from src.features.analyse_job.filters.preferences import (
    countries_fit,
    work_mode_fits,
)
from src.features.analyse_job.schemas import HardFilter, PostingTerms
from src.shared.models import Profile


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
