from hashlib import sha256


def job_key(posting_id: str) -> str:
    """The short id the agent sees for a posting, such as job-3f9a1c2e, since a
    source's own ids are too long for a model to copy"""
    return f"job-{sha256(posting_id.encode()).hexdigest()[:8]}"


__all__ = ["job_key"]
