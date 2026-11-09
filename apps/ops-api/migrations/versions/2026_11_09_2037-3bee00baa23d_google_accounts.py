"""google accounts

Revision ID: 3bee00baa23d
Revises: ab718d43ef41
Create Date: 2026-11-09 20:37:35.770438

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3bee00baa23d"
down_revision: str | Sequence[str] | None = "ab718d43ef41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "google_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_google_accounts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_google_accounts")),
    )
    op.enable_rls("google_accounts")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("google_accounts")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_table("google_accounts")
