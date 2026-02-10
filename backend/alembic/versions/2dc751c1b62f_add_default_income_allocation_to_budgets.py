"""add_default_income_allocation_to_budgets

Revision ID: 2dc751c1b62f
Revises: 66048a2e61bd
Create Date: 2026-01-15 21:02:06.988228

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2dc751c1b62f"
down_revision: str | None = "66048a2e61bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column(
            "default_income_allocation",
            sa.String(length=20),
            nullable=False,
            server_default="rules",
        ),
    )


def downgrade() -> None:
    op.drop_column("budgets", "default_income_allocation")
