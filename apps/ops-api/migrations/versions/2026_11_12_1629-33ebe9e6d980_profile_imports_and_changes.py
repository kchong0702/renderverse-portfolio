"""profile imports and changes

Revision ID: 33ebe9e6d980
Revises: 1d9ea7c54aa2
Create Date: 2026-11-12 16:29:44.260099

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "33ebe9e6d980"
down_revision: str | Sequence[str] | None = "1d9ea7c54aa2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "profile_imports",
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("added", sa.Integer(), nullable=False),
        sa.Column("conflicts", sa.Integer(), nullable=False),
        sa.Column("matched", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_by", sa.String(length=100), server_default="system", nullable=False
        ),
        sa.Column(
            "updated_by", sa.String(length=100), server_default="system", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profile_imports_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_imports")),
    )
    op.create_index(
        op.f("ix_profile_imports_user_id"), "profile_imports", ["user_id"], unique=False
    )
    op.create_table(
        "profile_changes",
        sa.Column("import_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=True),
        sa.Column("field", sa.String(length=20), nullable=True),
        sa.Column(
            "current",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column(
            "conflict",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column(
            "entry",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_by", sa.String(length=100), server_default="system", nullable=False
        ),
        sa.Column(
            "updated_by", sa.String(length=100), server_default="system", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["profile_entries.id"],
            name=op.f("fk_profile_changes_entry_id_profile_entries"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_id"],
            ["profile_imports.id"],
            name=op.f("fk_profile_changes_import_id_profile_imports"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profile_changes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_changes")),
    )
    op.create_index(
        op.f("ix_profile_changes_user_id"), "profile_changes", ["user_id"], unique=False
    )
    op.add_column(
        "profiles",
        sa.Column(
            "networking_aim", sa.String(length=200), server_default="", nullable=False
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "networking",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )
    op.enable_rls("profile_imports")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("profile_changes")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("profile_changes")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("profile_imports")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_column("profiles", "networking")
    op.drop_column("profiles", "networking_aim")
    op.drop_index(op.f("ix_profile_changes_user_id"), table_name="profile_changes")
    op.drop_table("profile_changes")
    op.drop_index(op.f("ix_profile_imports_user_id"), table_name="profile_imports")
    op.drop_table("profile_imports")
