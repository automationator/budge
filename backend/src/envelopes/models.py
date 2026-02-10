from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Envelope(Base):
    __tablename__ = "envelopes"
    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_budget_envelope_name"),
        Index(
            "ix_envelopes_budget_unallocated",
            "budget_id",
            unique=True,
            postgresql_where=text("is_unallocated = true"),
        ),
        Index("ix_envelopes_budget_group_id", "budget_id", "envelope_group_id"),
        # Ensure one CC envelope per account (linked_account_id is unique when not null)
        Index(
            "ix_envelopes_linked_account",
            "linked_account_id",
            unique=True,
            postgresql_where=text("linked_account_id IS NOT NULL"),
        ),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    envelope_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("envelope_groups.id", ondelete="SET NULL"),
        default=None,
    )
    # Link to credit card account (for CC envelopes that auto-track spending)
    linked_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        default=None,
    )
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str | None] = mapped_column(String(10), default=None)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_starred: Mapped[bool] = mapped_column(default=False)
    is_unallocated: Mapped[bool] = mapped_column(default=False)
    current_balance: Mapped[int] = mapped_column(
        BigInteger, default=0
    )  # Stored as cents to avoid floating point issues
    target_balance: Mapped[int | None] = mapped_column(
        BigInteger, default=None
    )  # Stored as cents, optional goal amount

    # Track when goal-reached notification was sent to avoid duplicates
    goal_reached_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
