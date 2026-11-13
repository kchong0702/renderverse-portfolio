from fastapi import Request
from fastapi.responses import JSONResponse

from src.clients.ezcareer import AgentRunFailed
from src.core.exceptions import ServiceException


async def service_exception(_: Request, error: ServiceException) -> JSONResponse:
    """Answer a ServiceException with its status code and message"""
    return JSONResponse(
        status_code=error.status_code, content={"detail": error.message}
    )


async def agent_run_failed(_: Request, error: AgentRunFailed) -> JSONResponse:
    """Answer a failed harness run with its reason and the screen that would help"""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "reason": error.message,
            "next": error.next.model_dump() if error.next else None,
        },
    )
