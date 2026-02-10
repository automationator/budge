"""split_account_balance

Revision ID: a2b3c4d5e6f7
Revises: 9dc3013ee865
Create Date: 2025-12-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "9dc3013ee865"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new columns with defaults
    op.add_column(
        "accounts",
        sa.Column(
            "cleared_balance", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "uncleared_balance", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )

    # Migrate existing data: calculate cleared and uncleared balances from transactions
    op.execute("""
        UPDATE accounts SET
            cleared_balance = COALESCE((
                SELECT SUM(amount)
                FROM transactions
                WHERE transactions.account_id = accounts.id
                  AND transactions.is_cleared = true
                  AND transactions.status = 'posted'
            ), 0),
            uncleared_balance = COALESCE((
                SELECT SUM(amount)
                FROM transactions
                WHERE transactions.account_id = accounts.id
                  AND transactions.is_cleared = false
                  AND transactions.status = 'posted'
            ), 0)
    """)

    # Remove the old column
    op.drop_column("accounts", "current_balance")

    # Remove the server defaults now that data is migrated
    op.alter_column("accounts", "cleared_balance", server_default=None)
    op.alter_column("accounts", "uncleared_balance", server_default=None)


def downgrade() -> None:
    # Add back current_balance
    op.add_column(
        "accounts",
        sa.Column(
            "current_balance", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )

    # Populate from cleared + uncleared
    op.execute("""
        UPDATE accounts SET
            current_balance = cleared_balance + uncleared_balance
    """)

    # Remove the new columns
    op.drop_column("accounts", "uncleared_balance")
    op.drop_column("accounts", "cleared_balance")

    # Remove server default
    op.alter_column("accounts", "current_balance", server_default=None)
