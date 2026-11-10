"""job runs and seen jobs

Revision ID: 8ccec88122f0
Revises: 88bf0218c892
Create Date: 2026-11-10 22:04:44.475111

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8ccec88122f0"
down_revision: str | Sequence[str] | None = "88bf0218c892"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "job_runs",
        sa.Column("found", sa.Integer(), nullable=False),
        sa.Column("new", sa.Integer(), nullable=False),
        sa.Column("scored_70", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_job_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_runs")),
    )
    op.create_index(op.f("ix_job_runs_user_id"), "job_runs", ["user_id"], unique=False)
    op.add_column(
        "jobs", sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.enable_rls("job_runs")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("job_runs")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_column("jobs", "seen_at")
    op.drop_index(op.f("ix_job_runs_user_id"), table_name="job_runs")
    op.drop_table("job_runs")
