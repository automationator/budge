from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class FrequencyUnit(StrEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        Index(
            "ix_recurring_transactions_budget_id",
            "budget_id",
        ),
        Index(
            "ix_recurring_transactions_budget_next_occurrence",
            "budget_id",
            "next_occurrence_date",
        ),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
    )
    # For transfers, this is the destination account
    destination_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        default=None,
    )
    # Null for transfers, required for regular transactions
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
    # Default envelope for auto-allocation when transactions are realized
    envelope_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("envelopes.id", ondelete="SET NULL"),
        default=None,
    )

    # Recurrence configuration
    frequency_value: Mapped[int] = mapped_column(Integer)
    frequency_unit: Mapped[FrequencyUnit] = mapped_column(
        PgEnum(
            FrequencyUnit,
            name="frequency_unit",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)

    # Template values
    amount: Mapped[int] = mapped_column(BigInteger)
    memo: Mapped[str | None] = mapped_column(String(500), default=None)

    # Generation tracking
    next_occurrence_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)
