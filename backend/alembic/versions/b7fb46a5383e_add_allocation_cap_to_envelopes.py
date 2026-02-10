"""add_allocation_cap_to_envelopes

Revision ID: b7fb46a5383e
Revises: 2dc751c1b62f
Create Date: 2026-01-18 01:24:32.515937

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7fb46a5383e"
down_revision: str | None = "2dc751c1b62f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum type first
    allocationcapperiodunit = sa.Enum(
        "WEEK", "MONTH", "YEAR", name="allocationcapperiodunit"
    )
    allocationcapperiodunit.create(op.get_bind(), checkfirst=True)

    # Add allocation cap fields to envelopes
    op.add_column(
        "envelopes", sa.Column("allocation_cap_amount", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "envelopes",
        sa.Column(
            "allocation_cap_period_value",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.add_column(
        "envelopes",
        sa.Column("allocation_cap_period_unit", allocationcapperiodunit, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("envelopes", "allocation_cap_period_unit")
    op.drop_column("envelopes", "allocation_cap_period_value")
    op.drop_column("envelopes", "allocation_cap_amount")

    # Drop enum type
    sa.Enum(name="allocationcapperiodunit").drop(op.get_bind(), checkfirst=True)
