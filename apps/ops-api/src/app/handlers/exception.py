from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.exceptions import ServiceException


async def service_exception(_: Request, error: ServiceException) -> JSONResponse:
    """Answer a ServiceException with its status code and message"""
    return JSONResponse(
        status_code=error.status_code, content={"detail": error.message}
    )
