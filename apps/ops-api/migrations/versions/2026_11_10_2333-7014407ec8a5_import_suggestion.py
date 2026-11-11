"""import_suggestion

Revision ID: 7014407ec8a5
Revises: 13ff13ef956d
Create Date: 2026-11-10 23:33:26.163297

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7014407ec8a5"
down_revision: str | Sequence[str] | None = "13ff13ef956d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "document_imports",
        sa.Column(
            "suggestion",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("document_imports", "suggestion")
