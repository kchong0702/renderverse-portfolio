from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import Tool, Tools
from src.features.jobs.tools.job_run import JobRunRequest, job_run


def job_tools(factory: async_sessionmaker[AsyncSession]) -> Tools:
    """The jobs' tools"""
    return {"job_run": Tool(JobRunRequest, partial(job_run, factory))}


__all__ = ["job_tools"]
