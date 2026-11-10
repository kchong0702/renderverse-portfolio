"""google grant scopes

Revision ID: 9c1d4e7a2b36
Revises: e9fac86ca563
Create Date: 2026-11-10 23:13:42.819074

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c1d4e7a2b36"
down_revision: str | Sequence[str] | None = "e9fac86ca563"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "google_accounts",
        sa.Column("scopes", sa.Text(), server_default="", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("google_accounts", "scopes")
