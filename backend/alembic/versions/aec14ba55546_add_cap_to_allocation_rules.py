"""add_cap_to_allocation_rules

Revision ID: aec14ba55546
Revises: c1a2b3d4e5f6
Create Date: 2026-02-01 11:58:08.807278

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aec14ba55546"
down_revision: str | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("allocation_rules", sa.Column("cap", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("allocation_rules", "cap")
