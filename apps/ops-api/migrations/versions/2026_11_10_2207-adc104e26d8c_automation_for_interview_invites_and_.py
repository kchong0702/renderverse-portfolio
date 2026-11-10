"""automation for interview invites and free slots

Revision ID: adc104e26d8c
Revises: 3bee00baa23d
Create Date: 2026-11-10 22:07:44.870294

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "adc104e26d8c"
down_revision: str | Sequence[str] | None = "3bee00baa23d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_settings",
        sa.Column(
            "add_interview_invites",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "offer_free_slots",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_settings", "offer_free_slots")
    op.drop_column("user_settings", "add_interview_invites")
