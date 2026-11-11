"""application next step details

Revision ID: 42cfe0c54d3a
Revises: 8ccec88122f0
Create Date: 2026-11-10 22:06:07.543489

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "42cfe0c54d3a"
down_revision: str | Sequence[str] | None = "8ccec88122f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("applications", sa.Column("next_step_due", sa.Date(), nullable=True))
    op.add_column(
        "applications", sa.Column("next_step_format", sa.String(), nullable=True)
    )
    op.add_column(
        "applications",
        sa.Column("next_step_location", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("applications", "next_step_location")
    op.drop_column("applications", "next_step_format")
    op.drop_column("applications", "next_step_due")
