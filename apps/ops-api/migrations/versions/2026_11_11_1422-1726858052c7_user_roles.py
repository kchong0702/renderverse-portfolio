"""user roles

Revision ID: 1726858052c7
Revises: 244f8520ebe0
Create Date: 2026-11-11 14:22:55.335762

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1726858052c7"
down_revision: str | Sequence[str] | None = "244f8520ebe0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users", sa.Column("role", sa.String(), server_default="user", nullable=False)
    )
    op.add_column(
        "users",
        sa.Column(
            "created_by", sa.String(length=100), server_default="system", nullable=False
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_by", sa.String(length=100), server_default="system", nullable=False
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "updated_at")
    op.drop_column("users", "updated_by")
    op.drop_column("users", "created_by")
    op.drop_column("users", "role")
