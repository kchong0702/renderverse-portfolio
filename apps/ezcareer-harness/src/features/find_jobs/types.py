from typing import Literal

DatePosted = Literal["all", "today", "3days", "week", "month"]
"""How recent a searched job must be"""

EmploymentType = Literal["FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"]
"""A kind of employment JSearch can filter by"""

JobRequirement = Literal[
    "under_3_years_experience",
    "more_than_3_years_experience",
    "no_experience",
    "no_degree",
]
"""An experience or education requirement JSearch can filter by"""
