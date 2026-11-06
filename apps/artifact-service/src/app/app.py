from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routes import router
from src.core.config import get_settings
from src.infrastructure import (
    configure_logging,
    configure_metrics,
    configure_tracing,
    shutdown_metrics,
    shutdown_tracing,
)

_settings = get_settings()


def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": _settings.app.version}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle manager"""
    yield

    shutdown_metrics()
    shutdown_tracing()


def create_app() -> FastAPI:
    """Create the FastAPI app, configuring observability for the serving process"""
    configure_logging(_settings)
    configure_tracing(_settings)
    configure_metrics(_settings)

    app = FastAPI(
        title=_settings.app.name.upper(),
        version=_settings.app.version,
        openapi_url=f"{_settings.app.route_prefix}/openapi.json",
        docs_url=f"{_settings.app.route_prefix}/docs",
        lifespan=lifespan,
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

    app.include_router(router, prefix=_settings.app.route_prefix)

    return app
