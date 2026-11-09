"""profile

Revision ID: efa71bef0ccc
Revises: f003f5183812
Create Date: 2026-11-09 11:32:58.727405

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "efa71bef0ccc"
down_revision: str | Sequence[str] | None = "f003f5183812"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "profile_entries",
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("organisation", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("start", sa.String(length=7), nullable=True),
        sa.Column("end", sa.String(length=7), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "highlights",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profile_entries_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_entries")),
    )
    op.create_index(
        op.f("ix_profile_entries_user_id"), "profile_entries", ["user_id"], unique=False
    )
    op.create_table(
        "profile_skills",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("group", sa.String(length=100), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profile_skills_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_skills")),
    )
    op.create_index(
        op.f("ix_profile_skills_user_id"), "profile_skills", ["user_id"], unique=False
    )
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column(
            "links",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "work_modes",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column(
            "countries",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column(
            "authorised_countries",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("min_salary_amount", sa.Integer(), nullable=True),
        sa.Column("min_salary_currency", sa.String(length=3), nullable=True),
        sa.Column("min_salary_period", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_profiles")),
    )
    op.enable_rls("profile_entries")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("profile_skills")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("profiles")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("profiles")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("profile_skills")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("profile_entries")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_table("profiles")
    op.drop_index(op.f("ix_profile_skills_user_id"), table_name="profile_skills")
    op.drop_table("profile_skills")
    op.drop_index(op.f("ix_profile_entries_user_id"), table_name="profile_entries")
    op.drop_table("profile_entries")
