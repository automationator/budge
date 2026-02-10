"""add_payee_default_envelope

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2025-12-19 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7g8h9"
down_revision: str | None = "b3c4d5e6f7g8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add default_envelope_id to payees table
    op.add_column(
        "payees",
        sa.Column("default_envelope_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payees_default_envelope",
        "payees",
        "envelopes",
        ["default_envelope_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Drop the user_preferences table (no longer needed)
    # Use try/except since the index or table may not exist
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if user_preferences table exists before dropping
    if "user_preferences" in inspector.get_table_names():
        op.drop_index(
            "ix_user_preferences_team_user",
            table_name="user_preferences",
            if_exists=True,
        )
        op.drop_table("user_preferences")

    # Drop the payee envelope suggestion index if it exists
    # (This index may not exist depending on migration state)
    indexes = [idx["name"] for idx in inspector.get_indexes("transactions")]
    if "ix_transactions_team_payee_date_id" in indexes:
        op.drop_index("ix_transactions_team_payee_date_id", table_name="transactions")


def downgrade() -> None:
    # Recreate the payee envelope suggestion index
    op.create_index(
        "ix_transactions_team_payee_date_id",
        "transactions",
        ["team_id", "payee_id", sa.text("date DESC"), sa.text("id DESC")],
        unique=False,
    )

    # Recreate user_preferences table
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

    # Remove default_envelope_id from payees
    op.drop_constraint("fk_payees_default_envelope", "payees", type_="foreignkey")
    op.drop_column("payees", "default_envelope_id")
