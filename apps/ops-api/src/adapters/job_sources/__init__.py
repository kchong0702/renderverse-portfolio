from src.adapters.job_sources.factory import build_job_source
from src.adapters.job_sources.protocol import JobSource
from src.adapters.job_sources.schemas import (
    JobPosting,
    JobQuery,
    JobSearchResults,
    PostingLine,
)

__all__ = [
    "JobPosting",
    "JobQuery",
    "JobSearchResults",
    "JobSource",
    "PostingLine",
    "build_job_source",
]
