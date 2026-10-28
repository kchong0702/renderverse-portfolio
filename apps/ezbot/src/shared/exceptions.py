from __future__ import annotations


class ModelConfigError(ValueError):
    """A configured model cannot be built"""


class MissingCredentialsError(ModelConfigError):
    """The model's API key environment variable is not set"""


class NoModelConfiguredError(ModelConfigError):
    """No configured model could be built"""


class PromptError(ValueError):
    """A prompt's variables do not match what it declares or receives"""


class SessionCapacityError(Exception):
    """The store is full; live sessions are never evicted to make room"""


class ResponseInProgressError(Exception):
    """The session already has a response streaming"""


class ResponseNotFoundError(Exception):
    """No resumable response matches the request"""


__all__ = [
    "MissingCredentialsError",
    "ModelConfigError",
    "NoModelConfiguredError",
    "PromptError",
    "ResponseInProgressError",
    "ResponseNotFoundError",
    "SessionCapacityError",
]
