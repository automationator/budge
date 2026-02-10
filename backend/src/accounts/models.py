from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_budget_account_name"),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[AccountType] = mapped_column(
        PgEnum(
            AccountType,
            name="account_type",
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
    )
    icon: Mapped[str | None] = mapped_column(String(10), default=None)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    include_in_budget: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    cleared_balance: Mapped[int] = mapped_column(
        BigInteger, default=0
    )  # Stored as cents to avoid floating point issues
    uncleared_balance: Mapped[int] = mapped_column(
        BigInteger, default=0
    )  # Stored as cents to avoid floating point issues
    last_reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
