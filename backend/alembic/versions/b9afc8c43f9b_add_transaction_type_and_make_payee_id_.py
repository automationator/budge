"""Add transaction_type and make payee_id nullable

Revision ID: b9afc8c43f9b
Revises: 30851f39d362
Create Date: 2025-12-01 13:14:29.084176

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9afc8c43f9b"
down_revision: str | None = "30851f39d362"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum type
    transaction_type_enum = postgresql.ENUM(
        "standard", "transfer", "adjustment", name="transaction_type", create_type=False
    )
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # Add column with server default for existing rows
    op.add_column(
        "transactions",
        sa.Column(
            "transaction_type",
            transaction_type_enum,
            nullable=False,
            server_default="standard",
        ),
    )

    # Remove server default (keep model default)
    op.alter_column("transactions", "transaction_type", server_default=None)

    # Make payee_id nullable
    op.alter_column("transactions", "payee_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column("transactions", "payee_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("transactions", "transaction_type")

    # Drop enum type
    transaction_type_enum = postgresql.ENUM(name="transaction_type")
    transaction_type_enum.drop(op.get_bind(), checkfirst=True)
