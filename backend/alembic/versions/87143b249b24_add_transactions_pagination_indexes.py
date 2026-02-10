"""add_transactions_pagination_indexes

Revision ID: 87143b249b24
Revises: bc70a9ed73d5
Create Date: 2025-12-01 01:53:00.503971

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87143b249b24"
down_revision: str | None = "bc70a9ed73d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Index for team-level keyset pagination (no account filter)
    op.create_index(
        "ix_transactions_team_date_id",
        "transactions",
        ["team_id", "date", "id"],
    )
    # Index for account-filtered keyset pagination
    op.create_index(
        "ix_transactions_team_account_date_id",
        "transactions",
        ["team_id", "account_id", "date", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_team_account_date_id", table_name="transactions")
    op.drop_index("ix_transactions_team_date_id", table_name="transactions")
