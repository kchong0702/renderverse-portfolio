"""documents tailored to a job

Revision ID: ab718d43ef41
Revises: 7014407ec8a5
Create Date: 2026-11-11 00:07:59.112913

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ab718d43ef41"
down_revision: str | Sequence[str] | None = "7014407ec8a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("job_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        op.f("uq_documents_job_id"), "documents", ["job_id", "kind"]
    )
    op.create_foreign_key(
        op.f("fk_documents_job_id_jobs"),
        "documents",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_documents_job_id_jobs"), "documents", type_="foreignkey"
    )
    op.drop_constraint(op.f("uq_documents_job_id"), "documents", type_="unique")
    op.drop_column("documents", "job_id")
