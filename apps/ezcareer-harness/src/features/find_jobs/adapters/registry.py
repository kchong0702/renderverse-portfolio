from src.features.find_jobs.adapters.base import JobAdapter
from src.features.find_jobs.adapters.jsearch import JSEARCH

ADAPTERS: dict[str, JobAdapter] = {JSEARCH.name: JSEARCH}
"""Every job source search_jobs can search, by the name job_sources enables it by"""
