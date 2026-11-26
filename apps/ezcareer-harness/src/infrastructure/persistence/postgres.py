import asyncio

from a2a.server.cluster import DatabaseTaskEventStream, VersionedDatabaseTaskStore
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import event, make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import DatabaseSettings


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """An async SQLAlchemy engine, for the A2A task store and event stream and the
    task owners, working in the harness's schema; Supabase's session pooler ignores a
    startup search_path"""
    engine = create_async_engine(
        settings.url.get_secret_value(),
        pool_size=settings.pool_size,
    )

    @event.listens_for(engine.sync_engine, "connect", insert=True)
    def _set_search_path(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{settings.schema_name}"')
        cursor.close()
        dbapi_connection.commit()

    return engine


def create_pool(settings: DatabaseSettings) -> AsyncConnectionPool:
    """A closed psycopg pool, for LangGraph's checkpointer, working in the harness's
    schema; open_postgres opens it"""

    async def set_search_path(connection: AsyncConnection) -> None:
        await connection.execute(f'SET search_path TO "{settings.schema_name}"')

    return AsyncConnectionPool(
        make_url(settings.url.get_secret_value())
        .set(drivername="postgresql")
        .render_as_string(hide_password=False),
        min_size=1,
        max_size=settings.pool_size,
        open=False,
        configure=set_search_path,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )


async def open_postgres(
    engine: AsyncEngine,
    pool: AsyncConnectionPool,
    schema_name: str,
    task_store: VersionedDatabaseTaskStore,
    event_stream: DatabaseTaskEventStream,
    checkpointer: AsyncPostgresSaver,
) -> None:
    """Opens the pool and creates the schema and the A2A and LangGraph tables, one
    process at a time, holding no transaction that LangGraph's index builds wait on"""
    await pool.open(wait=True)
    async with engine.connect() as connection:
        lock = await connection.execution_options(isolation_level="AUTOCOMMIT")
        while not await lock.scalar(
            text("SELECT pg_try_advisory_lock(hashtext('ezcareer setup'))")
        ):
            await asyncio.sleep(0.5)
        try:
            async with engine.begin() as ddl:
                await ddl.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            await task_store.initialize()
            await event_stream.initialize()
            await checkpointer.setup()
        finally:
            await lock.execute(
                text("SELECT pg_advisory_unlock(hashtext('ezcareer setup'))")
            )
