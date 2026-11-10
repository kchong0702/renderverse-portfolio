"""project on site

Revision ID: 5e120e23c614
Revises: 9c1d4e7a2b36
Create Date: 2026-11-11 01:30:23.699033

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e120e23c614"
down_revision: str | Sequence[str] | None = "9c1d4e7a2b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profile_entries",
        sa.Column(
            "on_site", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profile_entries", "on_site")
