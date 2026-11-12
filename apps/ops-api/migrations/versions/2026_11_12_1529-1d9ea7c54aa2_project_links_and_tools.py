"""project links and tools

Revision ID: 1d9ea7c54aa2
Revises: 1726858052c7
Create Date: 2026-11-12 15:29:19.492713

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1d9ea7c54aa2"
down_revision: str | Sequence[str] | None = "1726858052c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profile_entries", sa.Column("link", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "profile_entries", sa.Column("code_link", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "profile_entries",
        sa.Column(
            "tools",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profile_entries", "tools")
    op.drop_column("profile_entries", "code_link")
    op.drop_column("profile_entries", "link")
