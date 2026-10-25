from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.fastapi.v1.api import api_router as v1_router
from src.app.container import Container
from src.core.config import get_settings
from src.infrastructure import (
    configure_logging,
    configure_metrics,
    configure_tracing,
    instrument,
    shutdown_metrics,
    shutdown_tracing,
)

_settings = get_settings()

container = Container()


def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "ok", "version": _settings.app.version}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle manager"""
    container.wire(modules=["src.app.api.fastapi.deps"])

    app.state.container = container

    container.chat_service()
    store = container.session_store()
    store.start(on_sweep=container.message_limiter().sweep)

    yield

    await store.aclose()
    await container.intent_classifier().aclose()

    shutdown_metrics()
    shutdown_tracing()

    container.unwire()


def create_app() -> FastAPI:
    """Create FastAPI app, configuring observability for the serving process"""
    configure_logging(_settings)
    configure_tracing(_settings)
    configure_metrics(_settings)
    instrument(_settings)

    app = FastAPI(
        title=_settings.app.name.upper(),
        version=_settings.app.version,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in _settings.app.cors_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Content-Type",
            "Last-Event-ID",
            _settings.session.session_header,
        ],
        expose_headers=["Retry-After"],
    )

    app.include_router(router=v1_router, prefix=_settings.app.route_prefix)

    app.add_api_route(
        path="/health", endpoint=health_check, methods=["GET"], include_in_schema=True
    )

    return app
