from src.shared.profile.enums import FilterKind, SalaryPeriod, WorkMode
from src.shared.profile.preferences import (
    Preferences,
    Salary,
    countries_fit,
    work_mode_fits,
)
from src.shared.profile.profile import Profile
from src.shared.profile.profile_fact import ProfileFact, require_facts
from src.shared.profile.types import CountryCode, FactRef

__all__ = [
    "CountryCode",
    "FactRef",
    "FilterKind",
    "Preferences",
    "Profile",
    "ProfileFact",
    "Salary",
    "SalaryPeriod",
    "WorkMode",
    "countries_fit",
    "require_facts",
    "work_mode_fits",
]
