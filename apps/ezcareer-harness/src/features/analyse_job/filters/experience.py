from datetime import date

from src.shared.profile import ProfileFact


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
