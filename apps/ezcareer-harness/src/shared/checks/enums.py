from enum import StrEnum


class CheckRule(StrEnum):
    UNKNOWN_LINE = "unknown_line"
    """A cited posting or PDF line doesn't exist"""

    NOT_VERBATIM = "not_verbatim"
    """Requirement text isn't word for word in the lines it cites"""

    UNKNOWN_FACT = "unknown_fact"
    """A cited profile fact doesn't exist"""

    UNCITED_MATCH = "uncited_match"
    """A met or partly met requirement cites no fact"""

    UNKNOWN_JOB = "unknown_job"
    """A ranked job isn't one search_jobs returned"""

    DUPLICATE_JOB = "duplicate_job"
    """A job is ranked more than once"""

    BREAKS_PREFERENCES = "breaks_preferences"
    """A ranked job breaks the user's work mode or country preference"""

    NOT_APPLICABLE = "not_applicable"
    """A changeset's edits don't apply to the document"""

    LOCKED = "locked"
    """A changeset changes something only the user may change"""

    UNCITED = "uncited"
    """An edited value cites no source"""

    UNKNOWN_SOURCE = "unknown_source"
    """An edited value cites a PDF line or fact that doesn't exist"""

    UNSUPPORTED = "unsupported"
    """An edited value claims something its sources don't say"""

    NO_ANSWER = "no_answer"
    """The agent ended without a reply in its response format"""

    NO_CHANGESET = "no_changeset"
    """The agent ended without answering with a changeset"""

    SCHEMA = "schema"
    """An imported document doesn't fit the schema"""

    VERBATIM = "verbatim"
    """Imported text isn't word for word in the PDF lines it cites"""

    COVERAGE = "coverage"
    """An import leaves PDF lines out"""

    ORDER = "order"
    """An import puts PDF lines out of order"""
