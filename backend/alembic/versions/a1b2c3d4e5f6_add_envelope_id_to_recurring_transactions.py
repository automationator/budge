"""add envelope_id to recurring_transactions

Revision ID: a1b2c3d4e5f6
Revises: 79f4329bad93
Create Date: 2025-12-06 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "79f4329bad93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recurring_transactions",
        sa.Column("envelope_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_recurring_transactions_envelope_id",
        "recurring_transactions",
        "envelopes",
        ["envelope_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_recurring_transactions_envelope_id",
        "recurring_transactions",
        type_="foreignkey",
    )
    op.drop_column("recurring_transactions", "envelope_id")
