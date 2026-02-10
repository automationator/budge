from __future__ import annotations

from datetime import date as DateType
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.transactions.models import Transaction


class Allocation(Base):
    __tablename__ = "allocations"
    __table_args__ = (
        UniqueConstraint(
            "budget_id", "group_id", "execution_order", name="uq_allocation_group_order"
        ),
        Index("ix_allocations_budget_envelope_id", "budget_id", "envelope_id"),
        Index("ix_allocations_budget_transaction_id", "budget_id", "transaction_id"),
        Index("ix_allocations_budget_group_id", "budget_id", "group_id"),
        Index("ix_allocations_budget_rule_id", "budget_id", "allocation_rule_id"),
        Index(
            "ix_allocations_budget_envelope_date_id",
            "budget_id",
            "envelope_id",
            "date",
            "id",
        ),
    )

    # Foreign Keys
    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    envelope_id: Mapped[UUID] = mapped_column(
        ForeignKey("envelopes.id", ondelete="CASCADE"),
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        default=None,
    )
    allocation_rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("allocation_rules.id", ondelete="SET NULL"),
        default=None,
    )

    # Grouping and ordering
    group_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True))
    execution_order: Mapped[int] = mapped_column(Integer, default=0)

    # Amount in cents (positive for income/inflow, negative for expense/outflow)
    amount: Mapped[int] = mapped_column(BigInteger)

    # Optional memo for this allocation
    memo: Mapped[str | None] = mapped_column(String(500), default=None)

    # Date of the allocation (transaction date or transfer date)
    date: Mapped[DateType] = mapped_column(Date)

    # Relationships
    transaction: Mapped[Transaction | None] = relationship(
        "Transaction",
        back_populates="allocations",
    )
