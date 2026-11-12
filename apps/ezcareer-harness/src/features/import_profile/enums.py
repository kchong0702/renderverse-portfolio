from enum import StrEnum


class EntryKind(StrEnum):
    ROLE = "role"
    """A job the user held"""

    EDUCATION = "education"
    """A degree, course or school"""

    PROJECT = "project"
    """Something the user built or led"""
