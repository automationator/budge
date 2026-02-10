from __future__ import annotations

import enum
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AllocationCapPeriodUnit(enum.StrEnum):
    """Time period units for allocation caps."""

    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class AllocationRuleType(StrEnum):
    FILL_TO_TARGET = "fill_to_target"  # Fill until envelope.target_balance
    FIXED = "fixed"  # Allocate exact amount
    PERCENTAGE = "percentage"  # Allocate % of remaining funds
    REMAINDER = "remainder"  # Take whatever is left (weighted)
    PERIOD_CAP = "period_cap"  # Limit allocations per time period


class AllocationRule(Base):
    __tablename__ = "allocation_rules"
    __table_args__ = (
        Index("ix_allocation_rules_budget_priority", "budget_id", "priority"),
        Index("ix_allocation_rules_budget_envelope", "budget_id", "envelope_id"),
    )

    # Foreign Keys
    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    envelope_id: Mapped[UUID] = mapped_column(
        ForeignKey("envelopes.id", ondelete="CASCADE"),
    )

    # Rule configuration
    priority: Mapped[int] = mapped_column(Integer)  # Lower = executes first
    rule_type: Mapped[AllocationRuleType] = mapped_column(
        PgEnum(
            AllocationRuleType,
            name="allocation_rule_type",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
    )
    amount: Mapped[int] = mapped_column(BigInteger, default=0)  # Cents or basis points
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    name: Mapped[str | None] = mapped_column(String(100), default=None)
    respect_target: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Stop at envelope target

    # Period cap fields (used only for PERIOD_CAP rule type)
    cap_period_value: Mapped[int] = mapped_column(Integer, default=1)
    cap_period_unit: Mapped[AllocationCapPeriodUnit | None] = mapped_column(
        SQLEnum(AllocationCapPeriodUnit, name="allocationcapperiodunit"),
        default=None,
    )
