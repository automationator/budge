"""Models for in-app notifications."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class NotificationType(StrEnum):
    """Types of notifications the system can generate."""

    LOW_BALANCE = "low_balance"  # Envelope balance below threshold
    UPCOMING_EXPENSE = "upcoming_expense"  # Scheduled expense coming soon
    RECURRING_NOT_FUNDED = "recurring_not_funded"  # Recurring can't be covered
    GOAL_REACHED = "goal_reached"  # Savings goal target reached


class Notification(Base):
    """In-app notification record."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_budget_user_read", "budget_id", "user_id", "is_read"),
        Index("ix_notifications_budget_type", "budget_id", "notification_type"),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        default=None,  # null = all budget members
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        PgEnum(
            NotificationType,
            name="notification_type",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
    )
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(1000))

    # Related entity for linking to the notification source
    related_entity_type: Mapped[str | None] = mapped_column(
        String(50), default=None
    )  # envelope, transaction, recurring_transaction
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), default=None
    )

    is_read: Mapped[bool] = mapped_column(default=False)
    is_dismissed: Mapped[bool] = mapped_column(default=False)


class NotificationPreference(Base):
    """User preferences for notifications within a budget."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "budget_id", "user_id", "notification_type", name="uq_notification_pref"
        ),
        Index("ix_notification_preferences_budget_user", "budget_id", "user_id"),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        PgEnum(
            NotificationType,
            name="notification_type",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
    )

    is_enabled: Mapped[bool] = mapped_column(default=True)

    # Type-specific settings
    # For LOW_BALANCE: threshold in cents below which to notify
    low_balance_threshold: Mapped[int | None] = mapped_column(BigInteger, default=None)
    # For UPCOMING_EXPENSE: days ahead to notify
    upcoming_expense_days: Mapped[int | None] = mapped_column(default=None)
