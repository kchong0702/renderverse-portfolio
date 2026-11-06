from __future__ import annotations


class ServiceError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Unauthorized(ServiceError):
    """No valid session, or wrong credentials"""

    status_code = 401


class Forbidden(ServiceError):
    """Known caller, not allowed"""

    status_code = 403


class TooManyRequests(ServiceError):
    status_code = 429


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class InvalidInput(ServiceError):
    """Well-formed input that breaks a rule the schema cannot express"""

    status_code = 422


__all__ = [
    "Conflict",
    "Forbidden",
    "InvalidInput",
    "NotFound",
    "ServiceError",
    "TooManyRequests",
    "Unauthorized",
]
