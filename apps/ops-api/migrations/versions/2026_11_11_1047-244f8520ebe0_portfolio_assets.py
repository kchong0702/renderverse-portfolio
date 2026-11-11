"""portfolio assets

Revision ID: 244f8520ebe0
Revises: f75f6a5aa5ff
Create Date: 2026-11-11 10:47:52.062980

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "244f8520ebe0"
down_revision: str | Sequence[str] | None = "f75f6a5aa5ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assets",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_assets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("user_id", "sha256", name=op.f("uq_assets_user_id")),
    )
    op.create_index(op.f("ix_assets_user_id"), "assets", ["user_id"], unique=False)
    op.add_column("profile_entries", sa.Column("image_id", sa.Uuid(), nullable=True))
    op.add_column("profile_entries", sa.Column("video_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_profile_entries_image_id_assets"),
        "profile_entries",
        "assets",
        ["image_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_profile_entries_video_id_assets"),
        "profile_entries",
        "assets",
        ["video_id"],
        ["id"],
    )
    op.enable_rls("assets")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("assets")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_constraint(
        op.f("fk_profile_entries_video_id_assets"),
        "profile_entries",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_profile_entries_image_id_assets"),
        "profile_entries",
        type_="foreignkey",
    )
    op.drop_column("profile_entries", "video_id")
    op.drop_column("profile_entries", "image_id")
    op.drop_index(op.f("ix_assets_user_id"), table_name="assets")
    op.drop_table("assets")
