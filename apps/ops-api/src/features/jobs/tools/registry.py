from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.job_sources import JobSource
from src.core.agent_runner import Tool, Tools, WriteTool
from src.features.jobs.tools.job_run import JobRunRequest, job_run
from src.features.jobs.tools.job_search import JobSearchRequest, job_search
from src.features.jobs.tools.saved_jobs import SavedJobsRequest, saved_jobs
from src.features.jobs.tools.tailor_documents import (
    TailorDocumentsRequest,
    tailor_documents,
)

if TYPE_CHECKING:
    from src.app.container import Container


def job_tools(
    factory: async_sessionmaker[AsyncSession],
    source: JobSource,
    container: "Container",
) -> Tools:
    """The jobs' tools"""
    return {
        "job_run": WriteTool(JobRunRequest, job_run),
        "job_search": Tool(JobSearchRequest, partial(job_search, factory, source)),
        "saved_jobs": Tool(SavedJobsRequest, partial(saved_jobs, factory)),
        "tailor_documents": WriteTool(
            TailorDocumentsRequest, partial(tailor_documents, container)
        ),
    }


__all__ = ["job_tools"]
