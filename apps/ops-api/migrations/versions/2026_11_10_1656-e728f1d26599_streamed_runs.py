"""streamed runs

Revision ID: e728f1d26599
Revises: c43b4de26c43
Create Date: 2026-11-10 16:56:47.267730

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e728f1d26599"
down_revision: str | Sequence[str] | None = "c43b4de26c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "streamed_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_streamed_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_streamed_runs")),
    )
    op.create_index(
        op.f("ix_streamed_runs_key"), "streamed_runs", ["key"], unique=False
    )
    op.create_index(
        op.f("ix_streamed_runs_user_id"), "streamed_runs", ["user_id"], unique=False
    )
    op.create_table(
        "streamed_events",
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["streamed_runs.id"],
            name=op.f("fk_streamed_events_run_id_streamed_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_streamed_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "seq", name=op.f("pk_streamed_events")),
    )
    op.create_index(
        op.f("ix_streamed_events_user_id"), "streamed_events", ["user_id"], unique=False
    )
    op.enable_rls("streamed_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("streamed_events")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("streamed_events")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("streamed_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(op.f("ix_streamed_events_user_id"), table_name="streamed_events")
    op.drop_table("streamed_events")
    op.drop_index(op.f("ix_streamed_runs_user_id"), table_name="streamed_runs")
    op.drop_index(op.f("ix_streamed_runs_key"), table_name="streamed_runs")
    op.drop_table("streamed_runs")
