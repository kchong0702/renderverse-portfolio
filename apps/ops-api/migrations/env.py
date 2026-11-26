import asyncio
from logging.config import fileConfig
from typing import Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from alembic.runtime.plugins import Plugin
from sqlalchemy import text
from sqlalchemy.engine import Connection

from migrations.ext import rls
from src.core.config import get_settings
from src.db import models  # noqa: F401
from src.db.base import Base, EnumString, PydanticJson
from src.db.session import create_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings().database

Plugin.setup_plugin_from_module(rls, rls.PLUGIN_NAME)


def _include_name(name, type_, parent_names) -> bool:
    """Only manage ops-api's schema; Supabase owns auth, storage and the rest"""
    if type_ == "schema":
        return name in (None, settings.schema_name)
    return True


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Leave Alembic's own version table alone; it is reflected without a schema"""
    return not (type_ == "table" and name == "alembic_version")


def _render_item(
    type_: str, obj: object, autogen_context: AutogenContext
) -> str | Literal[False]:
    """Write an EnumString or PydanticJson column as the plain type it stores"""
    if type_ == "type" and isinstance(obj, EnumString):
        return "sa.String()"
    if type_ == "type" and isinstance(obj, PydanticJson):
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return 'sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")'
    return False


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it"""
    context.configure(
        url=settings.url.get_secret_value(),
        target_metadata=target_metadata,
        include_name=_include_name,
        include_object=_include_object,
        render_item=_render_item,
        version_table_schema=settings.schema_name,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Create ops-api's schema, then run the migrations, keeping their version there"""
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.schema_name}"'))
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=_include_name,
        include_object=_include_object,
        render_item=_render_item,
        version_table_schema=settings.schema_name,
        autogenerate_plugins=["alembic.autogenerate.*", rls.PLUGIN_NAME],
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_engine(settings)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
