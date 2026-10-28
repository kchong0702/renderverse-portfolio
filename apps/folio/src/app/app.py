from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.infrastructure.observability.logging import configure_logging

_settings = get_settings()


def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": _settings.app.version}


def create_app() -> FastAPI:
    """Create the FastAPI app"""
    configure_logging(_settings)

    app = FastAPI(
        title=_settings.app.name.upper(),
        version=_settings.app.version,
        openapi_url=f"{_settings.app.route_prefix}/openapi.json",
        docs_url=f"{_settings.app.route_prefix}/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in _settings.app.cors_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.add_api_route(
        path=f"{_settings.app.route_prefix}/health",
        endpoint=health_check,
        methods=["GET"],
    )

    return app
