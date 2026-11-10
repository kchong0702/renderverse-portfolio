"""agent runs

Revision ID: 5e0c49440946
Revises: c43b4de26c43
Create Date: 2026-11-10 18:12:49.348366

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e0c49440946"
down_revision: str | Sequence[str] | None = "c43b4de26c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_index(op.f("ix_agent_runs_key"), "agent_runs", ["key"], unique=False)
    op.create_index(
        op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False
    )
    op.create_table(
        "agent_events",
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["agent_runs.id"],
            name=op.f("fk_agent_events_run_id_agent_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "seq", name=op.f("pk_agent_events")),
    )
    op.create_index(
        op.f("ix_agent_events_user_id"), "agent_events", ["user_id"], unique=False
    )
    op.enable_rls("agent_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("agent_events")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("agent_events")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("agent_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(op.f("ix_agent_events_user_id"), table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_key"), table_name="agent_runs")
    op.drop_table("agent_runs")
