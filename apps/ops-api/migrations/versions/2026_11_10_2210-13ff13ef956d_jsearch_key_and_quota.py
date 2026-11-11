"""jsearch key and quota

Revision ID: 13ff13ef956d
Revises: 42cfe0c54d3a
Create Date: 2026-11-10 22:10:48.363013

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "13ff13ef956d"
down_revision: str | Sequence[str] | None = "42cfe0c54d3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_settings",
        sa.Column("jsearch_ciphertext", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("jsearch_quota_remaining", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_settings", sa.Column("jsearch_quota_limit", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_settings", "jsearch_quota_limit")
    op.drop_column("user_settings", "jsearch_quota_remaining")
    op.drop_column("user_settings", "jsearch_ciphertext")
