from __future__ import annotations

from src.adapters.storage.local import LocalStorage
from src.adapters.storage.protocol import Storage
from src.adapters.storage.r2 import R2Storage
from src.core.config import StorageSettings


def create_storage(settings: StorageSettings, route_prefix: str) -> Storage:
    """R2 once its settings are set, else local directories served by ops-api"""
    return (
        R2Storage(settings.r2)
        if settings.r2.configured
        else LocalStorage(
            settings.local_dir,
            settings.local_private_dir,
            f"{route_prefix}/v1/portfolio/uploads",
        )
    )


__all__ = ["create_storage"]
