from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.job_sources import JobSource
from src.core.agent_runner import Tool, Tools
from src.features.jobs.tools.job_run import JobRunRequest, job_run
from src.features.jobs.tools.job_search import JobSearchRequest, job_search


def job_tools(
    factory: async_sessionmaker[AsyncSession],
    source: JobSource,
) -> Tools:
    """The jobs' tools"""
    return {
        "job_run": Tool(JobRunRequest, partial(job_run, factory)),
        "job_search": Tool(JobSearchRequest, partial(job_search, factory, source)),
    }


__all__ = ["job_tools"]
