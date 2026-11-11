"""email threads

Revision ID: e9fac86ca563
Revises: adc104e26d8c
Create Date: 2026-11-10 22:14:09.878267

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9fac86ca563"
down_revision: str | Sequence[str] | None = "adc104e26d8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "email_threads",
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("last_message_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("decide_by", sa.Date(), nullable=True),
        sa.Column("interview_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_location", sa.String(length=500), nullable=True),
        sa.Column("event_id", sa.String(length=1024), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_email_threads_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_threads_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_threads")),
        sa.UniqueConstraint(
            "user_id", "thread_id", name=op.f("uq_email_threads_user_id")
        ),
    )
    op.create_index(
        op.f("ix_email_threads_user_id"), "email_threads", ["user_id"], unique=False
    )
    op.enable_rls("email_threads")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("email_threads")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(op.f("ix_email_threads_user_id"), table_name="email_threads")
    op.drop_table("email_threads")
