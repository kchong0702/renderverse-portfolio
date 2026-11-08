from src.features.find_jobs.adapters.base import SearchResult
from src.features.find_jobs.adapters.jsearch import JSEARCH
from src.shared.adapters import AdapterFactory

JOB_SOURCES = AdapterFactory[SearchResult](JSEARCH)
"""Every job source search_jobs can search, by the name job_sources enables it by"""
