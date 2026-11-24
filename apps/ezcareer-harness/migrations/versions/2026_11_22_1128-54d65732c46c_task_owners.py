"""task owners

Revision ID: 54d65732c46c
Revises:
Create Date: 2026-11-22 11:28:19.725477

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "54d65732c46c"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "task_owners",
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(
        "ix_task_owners_heartbeat", "task_owners", ["heartbeat_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_task_owners_heartbeat", table_name="task_owners")
    op.drop_table("task_owners")
