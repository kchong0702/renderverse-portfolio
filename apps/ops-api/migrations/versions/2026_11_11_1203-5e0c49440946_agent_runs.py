"""agent_runs

Revision ID: 5e0c49440946
Revises: c43b4de26c43
Create Date: 2026-11-11 12:03:16.066233

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5e0c49440946"
down_revision: str | Sequence[str] | None = "c43b4de26c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_model_calls",
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("agent", sa.String(length=100), nullable=False),
        sa.Column("node", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=False),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_micros", sa.BigInteger(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("stop_reason", sa.String(length=50), nullable=True),
        sa.Column("provider_request_id", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_model_calls_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_model_calls")),
    )
    op.create_index(
        op.f("ix_agent_model_calls_user_id"),
        "agent_model_calls",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_model_calls_user_id_created_at",
        "agent_model_calls",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("agent", sa.String(length=100), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_index(
        op.f("ix_agent_runs_thread_id"), "agent_runs", ["thread_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False
    )
    op.create_table(
        "agent_events",
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
    op.enable_rls("agent_model_calls")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("agent_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("agent_events")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("agent_events")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("agent_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("agent_model_calls")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(op.f("ix_agent_events_user_id"), table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_thread_id"), table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(
        "ix_agent_model_calls_user_id_created_at", table_name="agent_model_calls"
    )
    op.drop_index(op.f("ix_agent_model_calls_user_id"), table_name="agent_model_calls")
    op.drop_table("agent_model_calls")
