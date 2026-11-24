import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from src.agents import register_harness_profiles
from src.app.a2a import add_executable_routes
from src.app.container import Container
from src.app.threads import router as threads_router
from src.core.config import Family, get_settings
from src.infrastructure import (
    configure_logging,
    configure_metrics,
    configure_tracing,
    instrument,
    shutdown_metrics,
    shutdown_tracing,
)
from src.infrastructure.persistence import open_postgres

_settings = get_settings()


def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": _settings.app.version}


class FamilyModels(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    family: Family
    """The model family"""

    models: list[str]
    """Models a user can pick in that family"""


class ModelCatalog(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    families: list[FamilyModels]
    """Every family a user can pick from, with its models"""


def list_models() -> ModelCatalog:
    """The models a user can pick, by family, from [models]"""
    return ModelCatalog(
        families=[
            FamilyModels(family=family, models=list(models))
            for family, models in _settings.models.items()
        ]
    )


def create_app(container: Container | None = None) -> FastAPI:
    """Create the FastAPI app, configuring observability for the serving process;
    tests pass a container with overridden providers"""
    container = container or Container()
    settings = container.settings()
    configure_logging(_settings)
    configure_tracing(_settings)
    configure_metrics(_settings)
    instrument(_settings)
    register_harness_profiles(_settings.harness_profiles)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Opens the stores and keeps owning and taking over tasks; on shutdown hands
        its tasks to another process and closes the stores"""
        if settings.stores == "postgres":
            await open_postgres(
                container.engine(),
                container.pool(),
                settings.database.schema_name,
                container.task_store(),
                container.event_stream(),
                container.checkpointer(),
            )
        ownership = container.ownership()
        await ownership.sweep(app.state.handlers, container.task_store())
        keeper = asyncio.create_task(
            ownership.keep(app.state.handlers, container.task_store())
        )
        yield
        keeper.cancel()
        with suppress(asyncio.CancelledError):
            await keeper
        for handler in app.state.handlers.values():
            await handler.aclose()
        await ownership.owners.release()
        if settings.stores == "postgres":
            await container.pool().close()
            await container.engine().dispose()
        shutdown_metrics()
        shutdown_tracing()

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
    app.add_api_route(
        path=f"{_settings.app.route_prefix}/models",
        endpoint=list_models,
        methods=["GET"],
    )
    app.include_router(threads_router, prefix=_settings.app.route_prefix)
    app.state.handlers = add_executable_routes(
        app,
        container.executables(),
        container.task_store(),
        container.event_stream(),
        container.ownership(),
        _settings.app,
    )

    return app
