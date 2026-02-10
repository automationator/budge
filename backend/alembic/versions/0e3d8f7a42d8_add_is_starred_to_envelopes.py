"""add_is_starred_to_envelopes

Revision ID: 0e3d8f7a42d8
Revises: b7fb46a5383e
Create Date: 2026-01-18 19:38:23.379696

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0e3d8f7a42d8"
down_revision: str | None = "b7fb46a5383e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "envelopes",
        sa.Column("is_starred", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("envelopes", "is_starred")
