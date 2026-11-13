from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.jsearch import JSearchClient
from src.core.agent_runner import Tool, Tools
from src.core.config import JSearchSettings
from src.features.jobs.schemas import JobSearchRequest
from src.features.jobs.tools.job_run import JobRunRequest, job_run
from src.features.jobs.tools.job_search import job_search


def job_tools(
    factory: async_sessionmaker[AsyncSession],
    client: JSearchClient,
    settings: JSearchSettings,
) -> Tools:
    """The jobs' tools"""
    return {
        "job_run": Tool(JobRunRequest, partial(job_run, factory)),
        "job_search": Tool(
            JobSearchRequest, partial(job_search, factory, client, settings)
        ),
    }


__all__ = ["job_tools"]
