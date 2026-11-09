import os

import pytest
from alembic.runtime.plugins import Plugin
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("OPS_API_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set"),
]

CHECKED_SCHEMAS = ("public",)


async def test_every_table_has_row_level_security():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        rows = await connection.execute(
            text(
                """
                SELECT n.nspname || '.' || c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'r'
                  AND n.nspname = ANY(:schemas)
                  AND NOT c.relrowsecurity
                ORDER BY 1
                """
            ),
            {"schemas": list(CHECKED_SCHEMAS)},
        )
        unprotected = rows.scalars().all()
        tables = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind = 'r' AND n.nspname = 'public'"
            )
        )
    await engine.dispose()

    assert tables, "run the migrations before this test"
    assert unprotected == [], f"tables without row level security: {unprotected}"


async def test_autogenerate_enables_rls_where_it_is_off():
    from alembic.autogenerate import produce_migrations
    from alembic.runtime.migration import MigrationContext

    from migrations.ext import rls
    from src.app import models  # noqa: F401  (registers the tables)
    from src.core.db.base import Base

    plugin = Plugin(rls.PLUGIN_NAME)
    rls.setup(plugin)

    def upgrade_ops(connection) -> list[tuple]:
        connection.execute(text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))
        context = MigrationContext.configure(
            connection,
            opts={"autogenerate_plugins": ["alembic.autogenerate.*", rls.PLUGIN_NAME]},
        )
        script = produce_migrations(context, Base.metadata)
        assert script.upgrade_ops is not None
        return [operation.to_diff_tuple() for operation in script.upgrade_ops.ops]

    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        found = await connection.run_sync(upgrade_ops)
        await connection.rollback()
    await engine.dispose()
    plugin.remove()

    assert found == [("enable_rls", None, "users")]
