"""Add date to allocations

Revision ID: 8bdf0b8ed34c
Revises: b589155c376d
Create Date: 2026-01-22 00:26:48.151280

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8bdf0b8ed34c"
down_revision: str | None = "b589155c376d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add date column as nullable first
    op.add_column("allocations", sa.Column("date", sa.Date(), nullable=True))

    # Backfill: Use transaction date if available, else extract from UUID7
    # UUID7 stores millisecond timestamp in the first 48 bits (first 12 hex chars)
    op.execute("""
        UPDATE allocations a
        SET date = COALESCE(
            (SELECT t.date FROM transactions t WHERE t.id = a.transaction_id),
            date(to_timestamp((('x' || substr(a.id::text, 1, 8)
                || substr(a.id::text, 10, 4))::bit(48)::bigint) / 1000.0))
        )
    """)

    # Make column non-nullable
    op.alter_column("allocations", "date", nullable=False)

    # Create index for sorting by date within an envelope
    op.create_index(
        "ix_allocations_budget_envelope_date_id",
        "allocations",
        ["budget_id", "envelope_id", "date", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_allocations_budget_envelope_date_id", table_name="allocations")
    op.drop_column("allocations", "date")
