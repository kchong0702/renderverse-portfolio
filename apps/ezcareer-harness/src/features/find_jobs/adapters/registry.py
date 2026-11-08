from collections.abc import Callable

from src.features.find_jobs.adapters.jsearch import JSearchAdapter
from src.features.find_jobs.adapters.protocol import SearchProtocol

JOB_SOURCES: dict[str, Callable[[], SearchProtocol]] = {"jsearch": JSearchAdapter}
"""Every job source by the name config.toml's job_sources enables it by"""
