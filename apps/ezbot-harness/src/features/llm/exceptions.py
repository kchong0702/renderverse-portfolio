from __future__ import annotations


class ModelConfigError(ValueError):
    """A configured model cannot be built"""


class MissingCredentialsError(ModelConfigError):
    """The model's API key environment variable is not set"""


class NoModelConfiguredError(ModelConfigError):
    """No configured model could be built"""


__all__ = [
    "MissingCredentialsError",
    "ModelConfigError",
    "NoModelConfiguredError",
]
