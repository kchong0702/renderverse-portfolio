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

    UNKNOWN_SLOT = "unknown_slot"
    """A draft offers a time that isn't one of the user's free slots"""

    NO_ANSWER = "no_answer"
    """The agent ended without a reply in its response format"""

    SCHEMA = "schema"
    """An imported document doesn't fit the schema"""

    VERBATIM = "verbatim"
    """Imported text isn't word for word in the PDF lines or export rows it comes from"""

    MISSING = "missing"
    """Written copy leaves out a field or entry it was asked for"""

    TOO_LONG = "too_long"
    """Written copy is longer than its cap"""

    NOT_PLAIN = "not_plain"
    """Written copy uses Markdown or HTML instead of plain text"""

    COVERAGE = "coverage"
    """An import leaves PDF lines out"""

    ORDER = "order"
    """An import puts PDF lines out of order"""
