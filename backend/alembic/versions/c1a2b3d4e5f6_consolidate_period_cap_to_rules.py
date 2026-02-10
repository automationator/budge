"""Consolidate envelope allocation caps into PERIOD_CAP rule type

Revision ID: c1a2b3d4e5f6
Revises: 8bdf0b8ed34c
Create Date: 2026-02-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: str | None = "8bdf0b8ed34c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add 'period_cap' value to the allocation_rule_type enum
    op.execute("ALTER TYPE allocation_rule_type ADD VALUE IF NOT EXISTS 'period_cap'")

    # 2. Add cap_period_value and cap_period_unit to allocation_rules
    op.add_column(
        "allocation_rules",
        sa.Column("cap_period_value", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "allocation_rules",
        sa.Column(
            "cap_period_unit",
            sa.Enum(
                "WEEK",
                "MONTH",
                "YEAR",
                name="allocationcapperiodunit",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    # 3. Drop cap column from allocation_rules
    op.drop_column("allocation_rules", "cap")

    # 4. Drop allocation cap columns from envelopes
    op.drop_column("envelopes", "allocation_cap_amount")
    op.drop_column("envelopes", "allocation_cap_period_value")
    op.drop_column("envelopes", "allocation_cap_period_unit")


def downgrade() -> None:
    # Re-add allocation cap columns to envelopes
    op.add_column(
        "envelopes",
        sa.Column(
            "allocation_cap_period_unit",
            sa.Enum(
                "WEEK",
                "MONTH",
                "YEAR",
                name="allocationcapperiodunit",
                create_type=False,
            ),
            nullable=True,
        ),
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
        sa.Column("allocation_cap_amount", sa.BigInteger(), nullable=True),
    )

    # Re-add cap column to allocation_rules
    op.add_column(
        "allocation_rules",
        sa.Column("cap", sa.BigInteger(), nullable=True),
    )

    # Drop cap_period columns from allocation_rules
    op.drop_column("allocation_rules", "cap_period_unit")
    op.drop_column("allocation_rules", "cap_period_value")

    # Note: Cannot remove 'period_cap' from enum in downgrade
    # PostgreSQL doesn't support removing enum values
