from collections.abc import Iterable


def require_unique_ids(ids: Iterable[str], where: str) -> None:
    """Raises when an id appears twice"""
    seen = list(ids)
    if len(seen) != len(set(seen)):
        raise ValueError(f"ids must be unique in {where}")
