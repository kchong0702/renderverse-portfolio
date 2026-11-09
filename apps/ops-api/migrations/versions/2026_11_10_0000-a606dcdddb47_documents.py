"""documents

Revision ID: a606dcdddb47
Revises: 3ffd1e262ce0
Create Date: 2026-11-10 00:00:24.194069

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a606dcdddb47"
down_revision: str | Sequence[str] | None = "3ffd1e262ce0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "documents",
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("master", sa.Boolean(), nullable=False),
        sa.Column(
            "body",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_documents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(
        op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False
    )
    op.create_table(
        "document_changesets",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column(
            "changeset",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_changesets_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_document_changesets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_changesets")),
    )
    op.create_index(
        op.f("ix_document_changesets_document_id"),
        "document_changesets",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_changesets_user_id"),
        "document_changesets",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "document_imports",
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_imports_document_id_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_document_imports_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_imports")),
    )
    op.create_index(
        op.f("ix_document_imports_user_id"),
        "document_imports",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "document_versions",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column(
            "body",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_versions_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_document_versions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_user_id"),
        "document_versions",
        ["user_id"],
        unique=False,
    )
    op.enable_rls("documents")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("document_changesets")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("document_imports")  # pyright: ignore[reportAttributeAccessIssue]
    op.enable_rls("document_versions")  # pyright: ignore[reportAttributeAccessIssue]


def downgrade() -> None:
    """Downgrade schema."""
    op.disable_rls("document_versions")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("document_imports")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("document_changesets")  # pyright: ignore[reportAttributeAccessIssue]
    op.disable_rls("documents")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_index(op.f("ix_document_versions_user_id"), table_name="document_versions")
    op.drop_index(
        op.f("ix_document_versions_document_id"), table_name="document_versions"
    )
    op.drop_table("document_versions")
    op.drop_index(op.f("ix_document_imports_user_id"), table_name="document_imports")
    op.drop_table("document_imports")
    op.drop_index(
        op.f("ix_document_changesets_user_id"), table_name="document_changesets"
    )
    op.drop_index(
        op.f("ix_document_changesets_document_id"), table_name="document_changesets"
    )
    op.drop_table("document_changesets")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")
