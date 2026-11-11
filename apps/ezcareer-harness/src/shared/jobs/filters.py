from src.shared.jobs.types import JobPosting
from src.shared.profile import (
    FilterKind,
    Preferences,
    WorkMode,
    countries_fit,
    work_mode_fits,
)


def broken_filters(posting: JobPosting, preferences: Preferences) -> list[FilterKind]:
    """Hard filters the posting breaks, judged from JSearch's remote flag and
    country; a job that isn't remote may be onsite or hybrid"""
    modes = [WorkMode.REMOTE] if posting.remote else [WorkMode.ONSITE, WorkMode.HYBRID]
    return [
        kind
        for kind, fits in (
            (FilterKind.WORK_MODE, work_mode_fits(modes, preferences)),
            (
                FilterKind.LOCATION,
                posting.country is None
                or countries_fit([posting.country], preferences),
            ),
        )
        if not fits
    ]
