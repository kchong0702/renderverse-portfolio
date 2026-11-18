"""any sign-in provider

Revision ID: ca5380d27ab4
Revises: 19f0cf9cd465
Create Date: 2026-11-18 20:28:15.897897

"""

from collections.abc import Sequence

from alembic import op

revision: str = "ca5380d27ab4"
down_revision: str | Sequence[str] | None = "19f0cf9cd465"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        op.f("ck_auth_identities_provider"), "auth_identities", type_="check"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_check_constraint(
        op.f("ck_auth_identities_provider"),
        "auth_identities",
        "provider in ('password', 'google', 'github')",
    )
