import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.core.config import get_settings
from src.infrastructure.persistence import create_engine, metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata

settings = get_settings().database


def _include_name(name, type_, parent_names) -> bool:
    """Only manage the harness's own tables; a2a-sdk and LangGraph create theirs"""
    return type_ != "table" or name in target_metadata.tables


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode, emitting SQL to the script output"""
    url = settings.url.get_secret_value()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=_include_name,
        version_table_schema=settings.schema_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Create the harness's schema, then run the migrations, keeping their version
    there"""
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.schema_name}"'))
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=_include_name,
        version_table_schema=settings.schema_name,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create the harness's engine, whose search path is its schema, and associate
    a connection with the context"""
    connectable = create_engine(settings)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
