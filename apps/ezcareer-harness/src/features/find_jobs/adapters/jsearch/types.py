from typing import Literal

DatePosted = Literal["all", "today", "3days", "week", "month"]
"""How recent a job must be, as JSearch's date_posted takes it"""

EmploymentType = Literal["FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"]
"""Every kind of employment JSearch's employment_types takes"""

JobRequirement = Literal[
    "under_3_years_experience",
    "more_than_3_years_experience",
    "no_experience",
    "no_degree",
]
"""Every requirement JSearch's job_requirements takes"""
