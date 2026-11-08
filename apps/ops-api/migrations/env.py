import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.runtime.plugins import Plugin
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from migrations.ext import rls
from src.app import models  # noqa: F401
from src.core.config import get_settings
from src.core.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

Plugin.setup_plugin_from_module(rls, rls.PLUGIN_NAME)


def _include_name(name, type_, parent_names) -> bool:
    """Only manage the public schema; Supabase owns auth, storage and the rest"""
    if type_ == "schema":
        return name in (None, "public")
    return True


def _database_url() -> str:
    return get_settings().database.url.get_secret_value()


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it"""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        include_name=_include_name,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=_include_name,
        autogenerate_plugins=["alembic.autogenerate.*", rls.PLUGIN_NAME],
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_database_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
