from enum import StrEnum


class Screen(StrEnum):
    PORTFOLIO = "portfolio"
    """Where the user adds profile facts"""

    DOCUMENTS = "documents"
    """Where the user keeps résumés, CVs and cover letters"""

    JOBS = "jobs"
    """Where the user finds and tracks jobs"""

    SETTINGS = "settings"
    """Where the user connects accounts and adds keys"""
