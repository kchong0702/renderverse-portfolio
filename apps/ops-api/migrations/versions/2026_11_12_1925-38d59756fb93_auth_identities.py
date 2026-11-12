"""auth identities

Revision ID: 38d59756fb93
Revises: 33ebe9e6d980
Create Date: 2026-11-12 19:25:34.770468

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "38d59756fb93"
down_revision: str | Sequence[str] | None = "33ebe9e6d980"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("auth_sign_in_attempts")
    op.add_column(
        "auth_identities",
        sa.Column("secret_hash", sa.String(length=255), nullable=True),
    )
    op.alter_column(
        "auth_identities",
        "subject",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )
    op.create_unique_constraint(
        op.f("uq_auth_identities_user_id"), "auth_identities", ["user_id", "provider"]
    )
    op.add_column(
        "users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_column("users", "password_hash")
    op.create_table(
        "auth_sign_in_attempts",
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("value", sa.String(length=320), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "scope", "value", name=op.f("pk_auth_sign_in_attempts")
        ),
    )
    op.enable_rls("auth_sign_in_attempts")  # pyright: ignore[reportAttributeAccessIssue]
    op.create_check_constraint(
        op.f("ck_users_email_normalised"), "users", "email = lower(trim(email))"
    )
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role in ('admin', 'user')"
    )
    op.create_check_constraint(
        op.f("ck_auth_identities_provider"),
        "auth_identities",
        "provider in ('password', 'google', 'github')",
    )
    op.create_check_constraint(
        op.f("ck_auth_identities_subject"),
        "auth_identities",
        "(provider = 'password') = (subject is null)",
    )
    op.create_check_constraint(
        op.f("ck_auth_identities_secret_hash"),
        "auth_identities",
        "(provider = 'password') = (secret_hash is not null)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("ck_auth_identities_secret_hash"), "auth_identities", type_="check"
    )
    op.drop_constraint(
        op.f("ck_auth_identities_subject"), "auth_identities", type_="check"
    )
    op.drop_constraint(
        op.f("ck_auth_identities_provider"), "auth_identities", type_="check"
    )
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_email_normalised"), "users", type_="check")
    op.disable_rls("auth_sign_in_attempts")  # pyright: ignore[reportAttributeAccessIssue]
    op.drop_table("auth_sign_in_attempts")
    op.add_column(
        "users",
        sa.Column(
            "password_hash", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
    )
    op.drop_column("users", "disabled_at")
    op.drop_constraint(
        op.f("uq_auth_identities_user_id"), "auth_identities", type_="unique"
    )
    op.alter_column(
        "auth_identities",
        "subject",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
    op.drop_column("auth_identities", "secret_hash")
    op.create_table(
        "auth_sign_in_attempts",
        sa.Column("email", sa.VARCHAR(length=320), autoincrement=False, nullable=False),
        sa.Column("attempts", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "window_ends_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("email", name=op.f("pk_auth_sign_in_attempts")),
    )
    op.enable_rls("auth_sign_in_attempts")  # pyright: ignore[reportAttributeAccessIssue]
