"""model choice

Revision ID: c43b4de26c43
Revises: efa71bef0ccc
Create Date: 2026-11-09 23:59:01.245826

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c43b4de26c43"
down_revision: str | Sequence[str] | None = "efa71bef0ccc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_settings", sa.Column("ai_family", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "user_settings", sa.Column("ai_model", sa.String(length=100), nullable=True)
    )
    op.drop_column("user_settings", "ai_provider")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user_settings",
        sa.Column(
            "ai_provider", sa.VARCHAR(length=20), autoincrement=False, nullable=False
        ),
    )
    op.drop_column("user_settings", "ai_model")
    op.drop_column("user_settings", "ai_family")
