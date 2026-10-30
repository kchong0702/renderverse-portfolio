from fastapi import HTTPException


def api_error(
    status_code: int, code: str, message: str, **headers: str
) -> HTTPException:
    """HTTP error with a machine-readable `code`, as `{"detail": {code, message}}`"""
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers or None,
    )
