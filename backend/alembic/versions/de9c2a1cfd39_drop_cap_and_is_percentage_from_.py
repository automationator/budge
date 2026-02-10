"""drop_cap_and_is_percentage_from_allocation_rules

Revision ID: de9c2a1cfd39
Revises: aec14ba55546
Create Date: 2026-02-08 11:55:57.406235

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de9c2a1cfd39"
down_revision: str | None = "aec14ba55546"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("allocation_rules", "is_percentage")
    op.drop_column("allocation_rules", "cap")


def downgrade() -> None:
    op.add_column(
        "allocation_rules",
        sa.Column("cap", sa.BIGINT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "allocation_rules",
        sa.Column(
            "is_percentage",
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
