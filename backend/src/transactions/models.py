from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.allocations.models import Allocation


class TransactionStatus(StrEnum):
    SCHEDULED = "scheduled"  # Future transaction, date > today
    POSTED = "posted"  # Real transaction
    SKIPPED = "skipped"  # User explicitly skipped this occurrence


class TransactionType(StrEnum):
    STANDARD = "standard"  # Normal income/expense transaction
    TRANSFER = "transfer"  # Transfer between accounts
    ADJUSTMENT = "adjustment"  # Reconciliation adjustment


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Keyset pagination: budget_id -> date -> id
        Index(
            "ix_transactions_budget_date_id",
            "budget_id",
            "date",
            "id",
        ),
        # Keyset pagination with account filter: budget_id -> account_id -> date -> id
        Index(
            "ix_transactions_budget_account_date_id",
            "budget_id",
            "account_id",
            "date",
            "id",
        ),
        # Status-based queries: budget_id -> status -> date -> id
        Index(
            "ix_transactions_budget_status_date_id",
            "budget_id",
            "status",
            "date",
            "id",
        ),
        # Recurring transaction lookups
        Index(
            "ix_transactions_recurring_id",
            "recurring_transaction_id",
        ),
        # Linked transaction lookups (for transfers)
        Index(
            "ix_transactions_linked_id",
            "linked_transaction_id",
        ),
        # Payee-based queries (payee analysis report)
        Index(
            "ix_transactions_budget_payee_id",
            "budget_id",
            "payee_id",
        ),
        # Location-based queries (location spending report)
        Index(
            "ix_transactions_budget_location_id",
            "budget_id",
            "location_id",
        ),
        # Reconciled status filter with keyset pagination
        Index(
            "ix_transactions_budget_reconciled_date_id",
            "budget_id",
            "is_reconciled",
            "date",
            "id",
        ),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
    )
    payee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payees.id", ondelete="RESTRICT"),
        default=None,
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        default=None,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        default=None,
    )
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[int] = mapped_column(BigInteger)
    is_cleared: Mapped[bool] = mapped_column(default=False)
    is_reconciled: Mapped[bool] = mapped_column(default=False)
    memo: Mapped[str | None] = mapped_column(String(500), default=None)

    # Transaction type and status
    transaction_type: Mapped[TransactionType] = mapped_column(
        PgEnum(
            TransactionType,
            name="transaction_type",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=TransactionType.STANDARD,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        PgEnum(
            TransactionStatus,
            name="transaction_status",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=TransactionStatus.POSTED,
    )
    recurring_transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recurring_transactions.id", ondelete="SET NULL"),
        default=None,
    )
    occurrence_index: Mapped[int | None] = mapped_column(Integer, default=None)
    is_modified: Mapped[bool] = mapped_column(default=False)

    # Transfer linking - links two transactions that form a transfer
    linked_transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        default=None,
    )

    # Relationships
    allocations: Mapped[list[Allocation]] = relationship(
        "Allocation",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="Allocation.execution_order",
        lazy="raise",  # Force explicit loading via selectinload()
    )
    linked_transaction: Mapped[Transaction | None] = relationship(
        "Transaction",
        foreign_keys=[linked_transaction_id],
        remote_side="Transaction.id",
        lazy="raise",
    )

    @property
    def linked_account_id(self) -> UUID | None:
        if self.linked_transaction is not None:
            return self.linked_transaction.account_id
        return None
