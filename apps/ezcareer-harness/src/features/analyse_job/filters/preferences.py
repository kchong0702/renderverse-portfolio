from collections.abc import Collection

from src.shared.models import CountryCode, Preferences, WorkMode


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
