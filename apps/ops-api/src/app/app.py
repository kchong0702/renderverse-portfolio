import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.app.container import Container
from src.app.handlers.exception import service_exception
from src.app.routers import api_router
from src.core.auth.csrf import CSRFMiddleware
from src.core.config import Settings, get_settings
from src.core.exceptions import ServiceException
from src.core.logging import configure_logging


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    auth = settings.auth
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.app.cors_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=auth.secret_key.get_secret_value() or secrets.token_urlsafe(32),
        session_cookie="ops_oauth",
        max_age=10 * 60,
        path=settings.app.route_prefix,
        same_site="lax",
        https_only=auth.secure_cookies,
    )
    app.add_middleware(
        CSRFMiddleware,
        allowed_origins={_origin(auth.web_url)}
        | {_origin(o) for o in settings.app.cors_origin if o != "*"},
    )


def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": get_settings().app.version}


def create_app(container: Container | None = None) -> FastAPI:
    """Create the FastAPI app; tests pass a container with overridden providers"""
    settings = get_settings()
    configure_logging(settings)
    container = container or Container()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await container.engine().dispose()
        await container.ezcareer().aclose()

    app = FastAPI(
        title=settings.app.name.upper(),
        version=settings.app.version,
        openapi_url=f"{settings.app.route_prefix}/openapi.json",
        docs_url=f"{settings.app.route_prefix}/docs",
        lifespan=lifespan,
        exception_handlers={ServiceException: service_exception},
    )
    app.state.container = container
    app.state.session_factory = container.session_factory()
    app.state.oauth_providers = container.oauth_providers()
    app.state.ezcareer = container.ezcareer()

    _add_middleware(app, settings)

    app.include_router(router=api_router, prefix=settings.app.route_prefix)

    app.add_api_route(
        path=f"{settings.app.route_prefix}/health",
        endpoint=health_check,
        methods=["GET"],
    )

    return app
