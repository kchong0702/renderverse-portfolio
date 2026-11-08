from __future__ import annotations


class ServiceException(Exception):
    status_code = 400
    """HTTP status the handler answers with"""

    def __init__(self, message: str):
        """Keep the message the client gets back as the response detail"""
        super().__init__(message)
        self.message = message


class Unauthorized(ServiceException):
    status_code = 401
    """No valid session, or wrong credentials"""


class Forbidden(ServiceException):
    status_code = 403
    """Known caller, not allowed"""


class TooManyRequests(ServiceException):
    status_code = 429
    """Too many attempts in the current window"""


class NotFound(ServiceException):
    status_code = 404
    """The requested thing does not exist"""


class Conflict(ServiceException):
    status_code = 409
    """The request clashes with what is already stored"""


class InvalidInput(ServiceException):
    status_code = 422
    """Well-formed input that breaks a rule the schema cannot express"""


__all__ = [
    "Conflict",
    "Forbidden",
    "InvalidInput",
    "NotFound",
    "ServiceException",
    "TooManyRequests",
    "Unauthorized",
]
