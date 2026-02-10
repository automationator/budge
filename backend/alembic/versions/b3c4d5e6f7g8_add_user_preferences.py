"""add_user_preferences

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2025-12-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7g8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create user_preferences table
    op.create_table(
        "user_preferences",
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "envelope_autofill_mode",
            sa.String(length=20),
            nullable=False,
            server_default="most_common",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_user_preferences"),
    )
    op.create_index(
        "ix_user_preferences_team_user",
        "user_preferences",
        ["team_id", "user_id"],
        unique=False,
    )

    # Add index for payee envelope suggestions (most recent queries)
    op.create_index(
        "ix_transactions_team_payee_date_id",
        "transactions",
        ["team_id", "payee_id", sa.text("date DESC"), sa.text("id DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_team_payee_date_id", table_name="transactions")
    op.drop_index("ix_user_preferences_team_user", table_name="user_preferences")
    op.drop_table("user_preferences")
