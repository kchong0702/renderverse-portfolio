"""portfolio releases

Revision ID: f75f6a5aa5ff
Revises: 5e120e23c614
Create Date: 2026-11-11 01:32:24.180298

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f75f6a5aa5ff"
down_revision: str | Sequence[str] | None = "5e120e23c614"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "portfolio_releases",
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("live", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_portfolio_releases_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolio_releases")),
        sa.UniqueConstraint(
            "user_id", "number", name=op.f("uq_portfolio_releases_user_id")
        ),
    )
    op.create_index(
        op.f("ix_portfolio_releases_user_id"),
        "portfolio_releases",
        ["user_id"],
        unique=False,
    )
    op.enable_rls("portfolio_releases")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("portfolio_releases")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(
        op.f("ix_portfolio_releases_user_id"), table_name="portfolio_releases"
    )
    op.drop_table("portfolio_releases")
