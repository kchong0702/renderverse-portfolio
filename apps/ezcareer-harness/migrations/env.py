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

settings = get_settings().database


def _include_name(name, type_, parent_names) -> bool:
    """Only manage the harness's own tables; a2a-sdk and LangGraph create theirs"""
    return type_ != "table" or name in metadata.tables


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it"""
    context.configure(
        url=settings.url.get_secret_value(),
        target_metadata=metadata,
        include_name=_include_name,
        version_table_schema=settings.schema_name,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run the migrations in the harness's schema, keeping their version there"""
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.schema_name}"'))
    context.configure(
        connection=connection,
        target_metadata=metadata,
        include_name=_include_name,
        version_table_schema=settings.schema_name,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run the migrations on the harness's engine, whose search path is its schema"""
    engine = create_engine(settings)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
