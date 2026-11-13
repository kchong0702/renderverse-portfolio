from __future__ import annotations

from typing import Literal

from src.adapters.job_sources.jsearch import JSearchSource
from src.adapters.job_sources.protocol import JobSource
from src.core.config import JSearchSettings


def build_job_source(source: Literal["jsearch"], jsearch: JSearchSettings) -> JobSource:
    """The job source the settings name"""
    match source:
        case "jsearch":
            return JSearchSource(jsearch)


__all__ = ["build_job_source"]
