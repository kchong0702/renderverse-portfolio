from __future__ import annotations

from typing import override

from alembic.autogenerate import renderers
from alembic.autogenerate.api import AutogenContext
from alembic.operations import MigrateOperation, Operations
from alembic.operations.ops import UpgradeOps
from alembic.runtime.plugins import Plugin
from alembic.util import DispatchPriority, PriorityDispatchResult
from sqlalchemy import text

PLUGIN_NAME = "ops_api.rls"

# Roles only exist on Supabase
API_ROLES = ("anon", "authenticated")

_IGNORE_PLUGIN_OP = "  # pyright: ignore[reportAttributeAccessIssue]"


class EnableRLSOp(MigrateOperation):
    """Enable row level security on a table and revoke the API roles' grants."""

    def __init__(self, table_name: str, schema: str | None = None):
        self.table_name = table_name
        self.schema = schema

    @classmethod
    def enable_rls(
        cls, operations: Operations, table_name: str, schema: str | None = None
    ) -> None:
        """Issue "ALTER TABLE ... ENABLE ROW LEVEL SECURITY" and revoke API grants."""
        operations.invoke(cls(table_name, schema=schema))

    @override
    def reverse(self) -> DisableRLSOp:
        return DisableRLSOp(self.table_name, schema=self.schema)

    @override
    def to_diff_tuple(self) -> tuple[str, str | None, str]:
        return ("enable_rls", self.schema, self.table_name)


class DisableRLSOp(MigrateOperation):
    """Disable row level security on a table; grants are left as they are."""

    def __init__(self, table_name: str, schema: str | None = None):
        self.table_name = table_name
        self.schema = schema

    @classmethod
    def disable_rls(
        cls, operations: Operations, table_name: str, schema: str | None = None
    ) -> None:
        """Issue "ALTER TABLE ... DISABLE ROW LEVEL SECURITY"."""
        operations.invoke(cls(table_name, schema=schema))

    @override
    def reverse(self) -> EnableRLSOp:
        return EnableRLSOp(self.table_name, schema=self.schema)

    @override
    def to_diff_tuple(self) -> tuple[str, str | None, str]:
        return ("disable_rls", self.schema, self.table_name)


def _table(operations: Operations, operation: EnableRLSOp | DisableRLSOp) -> str:
    preparer = operations.get_context().dialect.identifier_preparer
    name = preparer.quote(operation.table_name)
    if operation.schema is None:
        return name
    return f"{preparer.quote_schema(operation.schema)}.{name}"


def enable_rls(operations: Operations, operation: EnableRLSOp) -> None:
    table = _table(operations, operation)
    roles = ", ".join(f"'{role}'" for role in API_ROLES)
    operations.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    operations.execute(
        f"""
        DO $$
        DECLARE role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY[{roles}] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON TABLE {table} FROM %I', role_name);
                END IF;
            END LOOP;
        END $$
        """
    )


def disable_rls(operations: Operations, operation: DisableRLSOp) -> None:
    operations.execute(
        f"ALTER TABLE {_table(operations, operation)} DISABLE ROW LEVEL SECURITY"
    )


def _render_args(op: EnableRLSOp | DisableRLSOp) -> str:
    schema = f", schema={op.schema!r}" if op.schema is not None else ""
    return f"{op.table_name!r}{schema}"


def render_enable_rls(autogen_context: AutogenContext, op: EnableRLSOp) -> str:
    return f"op.enable_rls({_render_args(op)}){_IGNORE_PLUGIN_OP}"


def render_disable_rls(autogen_context: AutogenContext, op: DisableRLSOp) -> str:
    return f"op.disable_rls({_render_args(op)}){_IGNORE_PLUGIN_OP}"


def compare_rls(
    autogen_context: AutogenContext,
    upgrade_ops: UpgradeOps,
    schemas: set[str | None],
) -> PriorityDispatchResult:
    """Enable RLS on each model table, and Alembic's version table, that is new or
    has it off. Runs after the tables comparator, so it follows create_table."""
    assert autogen_context.connection is not None and autogen_context.dialect
    migration_context = autogen_context.migration_context

    for schema in sorted(schemas, key=lambda name: name or ""):
        rows = autogen_context.connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind = 'r' AND n.nspname = :nspname"
            ),
            {"nspname": schema or autogen_context.dialect.default_schema_name},
        )
        rls_enabled = {name: enabled for name, enabled in rows}

        tables = [
            table.name
            for table in autogen_context.sorted_tables
            if table.schema == schema
            and autogen_context.run_object_filters(
                table, table.name, "table", False, None
            )
        ]
        if migration_context.version_table_schema == schema:
            tables.append(migration_context.version_table)

        for name in tables:
            if not rls_enabled.get(name, False):
                upgrade_ops.ops.append(EnableRLSOp(name, schema=schema))

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    """Called by Plugin.setup_plugin_from_module()"""
    Operations.register_operation("enable_rls")(EnableRLSOp)
    Operations.register_operation("disable_rls")(DisableRLSOp)
    Operations.implementation_for(EnableRLSOp)(enable_rls)
    Operations.implementation_for(DisableRLSOp)(disable_rls)

    renderers.dispatch_for(EnableRLSOp)(render_enable_rls)
    renderers.dispatch_for(DisableRLSOp)(render_disable_rls)

    plugin.add_autogenerate_comparator(
        compare_rls,
        "schema",
        "rls",
        qualifier="postgresql",
        priority=DispatchPriority.LAST,
    )
