"""Service for notification generation and management."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.envelopes.models import Envelope
from src.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationType,
)
from src.payees.models import Payee
from src.recurring_transactions.models import RecurringTransaction
from src.transactions.models import Transaction, TransactionStatus


async def get_notifications(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
    include_dismissed: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """Get notifications for a user in a budget.

    Args:
        session: Database session
        budget_id: Budget to get notifications for
        user_id: User to get notifications for
        include_dismissed: Whether to include dismissed notifications
        limit: Maximum notifications to return

    Returns:
        List of notifications, newest first
    """
    query = (
        select(Notification)
        .where(
            Notification.budget_id == budget_id,
            or_(Notification.user_id == user_id, Notification.user_id.is_(None)),
        )
        .order_by(Notification.id.desc())
        .limit(limit)
    )

    if not include_dismissed:
        query = query.where(Notification.is_dismissed == False)  # noqa: E712

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_unread_count(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
) -> int:
    """Get count of unread notifications for a user."""
    query = select(func.count(Notification.id)).where(
        Notification.budget_id == budget_id,
        or_(Notification.user_id == user_id, Notification.user_id.is_(None)),
        Notification.is_read == False,  # noqa: E712
        Notification.is_dismissed == False,  # noqa: E712
    )

    result = await session.execute(query)
    return result.scalar() or 0


async def mark_notifications_read(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
    notification_ids: list[UUID],
) -> int:
    """Mark notifications as read.

    Returns:
        Number of notifications updated
    """
    stmt = (
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.budget_id == budget_id,
            or_(Notification.user_id == user_id, Notification.user_id.is_(None)),
        )
        .values(is_read=True)
    )

    result = await session.execute(stmt)
    return result.rowcount


async def mark_notifications_dismissed(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
    notification_ids: list[UUID],
) -> int:
    """Mark notifications as dismissed.

    Returns:
        Number of notifications updated
    """
    stmt = (
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.budget_id == budget_id,
            or_(Notification.user_id == user_id, Notification.user_id.is_(None)),
        )
        .values(is_dismissed=True)
    )

    result = await session.execute(stmt)
    return result.rowcount


async def get_preferences(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
) -> list[NotificationPreference]:
    """Get notification preferences for a user in a budget."""
    query = select(NotificationPreference).where(
        NotificationPreference.budget_id == budget_id,
        NotificationPreference.user_id == user_id,
    )

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_or_create_preference(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
    notification_type: NotificationType,
) -> NotificationPreference:
    """Get or create a notification preference."""
    query = select(NotificationPreference).where(
        NotificationPreference.budget_id == budget_id,
        NotificationPreference.user_id == user_id,
        NotificationPreference.notification_type == notification_type,
    )

    result = await session.execute(query)
    pref = result.scalar_one_or_none()

    if pref is None:
        # Create with defaults
        pref = NotificationPreference(
            id=uuid7(),
            budget_id=budget_id,
            user_id=user_id,
            notification_type=notification_type,
            is_enabled=True,
            low_balance_threshold=0
            if notification_type == NotificationType.LOW_BALANCE
            else None,
            upcoming_expense_days=7
            if notification_type == NotificationType.UPCOMING_EXPENSE
            else None,
        )
        session.add(pref)
        await session.flush()

    return pref


async def update_preference(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
    notification_type: NotificationType,
    is_enabled: bool | None = None,
    low_balance_threshold: int | None = None,
    upcoming_expense_days: int | None = None,
) -> NotificationPreference:
    """Update a notification preference."""
    pref = await get_or_create_preference(
        session, budget_id, user_id, notification_type
    )

    if is_enabled is not None:
        pref.is_enabled = is_enabled
    if (
        low_balance_threshold is not None
        and notification_type == NotificationType.LOW_BALANCE
    ):
        pref.low_balance_threshold = low_balance_threshold
    if (
        upcoming_expense_days is not None
        and notification_type == NotificationType.UPCOMING_EXPENSE
    ):
        pref.upcoming_expense_days = upcoming_expense_days

    return pref


async def generate_notifications(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
) -> list[Notification]:
    """Generate notifications based on current data state.

    This is called on-demand to check for notification conditions.
    Notifications are deduplicated to avoid spamming users.

    Args:
        session: Database session
        budget_id: Budget to generate notifications for
        user_id: User to generate notifications for

    Returns:
        List of newly created notifications
    """
    new_notifications: list[Notification] = []

    # Get user preferences (create defaults if not exist)
    prefs = await get_preferences(session, budget_id, user_id)
    pref_map = {p.notification_type: p for p in prefs}

    # Generate each notification type if enabled
    low_balance_pref = pref_map.get(NotificationType.LOW_BALANCE)
    if low_balance_pref is None or low_balance_pref.is_enabled:
        threshold = low_balance_pref.low_balance_threshold if low_balance_pref else 0
        new_notifications.extend(
            await _generate_low_balance_notifications(session, budget_id, threshold)
        )

    upcoming_pref = pref_map.get(NotificationType.UPCOMING_EXPENSE)
    if upcoming_pref is None or upcoming_pref.is_enabled:
        days = upcoming_pref.upcoming_expense_days if upcoming_pref else 7
        new_notifications.extend(
            await _generate_upcoming_expense_notifications(
                session, budget_id, days or 7
            )
        )

    recurring_pref = pref_map.get(NotificationType.RECURRING_NOT_FUNDED)
    if recurring_pref is None or recurring_pref.is_enabled:
        new_notifications.extend(
            await _generate_recurring_not_funded_notifications(session, budget_id)
        )

    goal_pref = pref_map.get(NotificationType.GOAL_REACHED)
    if goal_pref is None or goal_pref.is_enabled:
        new_notifications.extend(
            await _generate_goal_reached_notifications(session, budget_id)
        )

    # Flush changes (especially goal_reached_notified_at updates)
    await session.flush()

    return new_notifications


async def _generate_low_balance_notifications(
    session: AsyncSession,
    budget_id: UUID,
    threshold: int | None,
) -> list[Notification]:
    """Generate low balance notifications for envelopes below threshold."""
    if threshold is None:
        threshold = 0

    # Find active envelopes with balance <= threshold (excluding unallocated)
    query = select(Envelope).where(
        Envelope.budget_id == budget_id,
        Envelope.is_active == True,  # noqa: E712
        Envelope.is_unallocated == False,  # noqa: E712
        Envelope.current_balance <= threshold,
    )

    result = await session.execute(query)
    envelopes = result.scalars().all()

    new_notifications = []
    for envelope in envelopes:
        # Check if we already have a recent unread notification for this envelope
        existing = await _get_recent_notification(
            session,
            budget_id,
            NotificationType.LOW_BALANCE,
            "envelope",
            envelope.id,
        )
        if existing:
            continue

        # Create new notification
        balance_dollars = envelope.current_balance / 100
        threshold_dollars = threshold / 100

        notification = Notification(
            id=uuid7(),
            budget_id=budget_id,
            user_id=None,  # All budget members
            notification_type=NotificationType.LOW_BALANCE,
            title=f"Low balance: {envelope.name}",
            message=f"{envelope.name} balance is ${balance_dollars:.2f}, below the ${threshold_dollars:.2f} threshold.",
            related_entity_type="envelope",
            related_entity_id=envelope.id,
        )
        session.add(notification)
        new_notifications.append(notification)

    return new_notifications


async def _generate_upcoming_expense_notifications(
    session: AsyncSession,
    budget_id: UUID,
    days_ahead: int,
) -> list[Notification]:
    """Generate notifications for upcoming expenses that need attention."""
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    # Find scheduled expenses that need attention (underfunded or not linked)
    query = (
        select(
            Transaction.id.label("transaction_id"),
            Transaction.date,
            Transaction.amount,
            Payee.name.label("payee_name"),
            RecurringTransaction.envelope_id,
            Envelope.name.label("envelope_name"),
            Envelope.current_balance.label("envelope_balance"),
        )
        .outerjoin(Payee, Transaction.payee_id == Payee.id)
        .outerjoin(
            RecurringTransaction,
            Transaction.recurring_transaction_id == RecurringTransaction.id,
        )
        .outerjoin(Envelope, RecurringTransaction.envelope_id == Envelope.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.SCHEDULED,
            Transaction.date >= today,
            Transaction.date <= horizon,
            Transaction.amount < 0,  # Expenses only
        )
        .order_by(Transaction.date)
    )

    result = await session.execute(query)
    new_notifications = []

    for row in result.all():
        # Only create notifications for expenses that need attention
        needs_attention = False
        if (
            row.envelope_id is None
            or row.envelope_balance is not None
            and row.envelope_balance < abs(row.amount)
        ):
            needs_attention = True

        if not needs_attention:
            continue

        # Check for existing notification
        existing = await _get_recent_notification(
            session,
            budget_id,
            NotificationType.UPCOMING_EXPENSE,
            "transaction",
            row.transaction_id,
        )
        if existing:
            continue

        days_away = (row.date - today).days
        amount_dollars = abs(row.amount) / 100
        payee = row.payee_name or "Unknown payee"

        if row.envelope_id is None:
            message = f"${amount_dollars:.2f} expense to {payee} in {days_away} days has no linked envelope."
        else:
            balance_dollars = (row.envelope_balance or 0) / 100
            message = f"${amount_dollars:.2f} expense to {payee} in {days_away} days. {row.envelope_name} only has ${balance_dollars:.2f}."

        notification = Notification(
            id=uuid7(),
            budget_id=budget_id,
            user_id=None,
            notification_type=NotificationType.UPCOMING_EXPENSE,
            title="Upcoming expense needs attention",
            message=message,
            related_entity_type="transaction",
            related_entity_id=row.transaction_id,
        )
        session.add(notification)
        new_notifications.append(notification)

    return new_notifications


async def _generate_recurring_not_funded_notifications(
    session: AsyncSession,
    budget_id: UUID,
) -> list[Notification]:
    """Generate notifications for recurring expenses that can't be covered."""
    # Find active recurring expenses that are underfunded
    query = (
        select(
            RecurringTransaction.id,
            RecurringTransaction.amount,
            RecurringTransaction.envelope_id,
            Payee.name.label("payee_name"),
            Envelope.name.label("envelope_name"),
            Envelope.current_balance.label("envelope_balance"),
        )
        .outerjoin(Payee, RecurringTransaction.payee_id == Payee.id)
        .outerjoin(Envelope, RecurringTransaction.envelope_id == Envelope.id)
        .where(
            RecurringTransaction.budget_id == budget_id,
            RecurringTransaction.is_active == True,  # noqa: E712
            RecurringTransaction.amount < 0,  # Expenses only
        )
    )

    result = await session.execute(query)
    new_notifications = []

    for row in result.all():
        expense_amount = abs(row.amount)

        # Check if underfunded
        if row.envelope_id is None:
            # Not linked - skip (handled by upcoming_expense if scheduled)
            continue
        if row.envelope_balance is not None and row.envelope_balance >= expense_amount:
            # Fully funded
            continue

        # Check for existing notification
        existing = await _get_recent_notification(
            session,
            budget_id,
            NotificationType.RECURRING_NOT_FUNDED,
            "recurring_transaction",
            row.id,
        )
        if existing:
            continue

        amount_dollars = expense_amount / 100
        payee = row.payee_name or "Unknown payee"
        shortfall_dollars = (expense_amount - (row.envelope_balance or 0)) / 100

        notification = Notification(
            id=uuid7(),
            budget_id=budget_id,
            user_id=None,
            notification_type=NotificationType.RECURRING_NOT_FUNDED,
            title="Recurring expense underfunded",
            message=f"${amount_dollars:.2f} recurring expense to {payee} needs ${shortfall_dollars:.2f} more in {row.envelope_name}.",
            related_entity_type="recurring_transaction",
            related_entity_id=row.id,
        )
        session.add(notification)
        new_notifications.append(notification)

    return new_notifications


async def _generate_goal_reached_notifications(
    session: AsyncSession,
    budget_id: UUID,
) -> list[Notification]:
    """Generate notifications for envelopes that have reached their target."""
    now = datetime.now(UTC)

    # Find envelopes that have reached their goal and haven't been notified
    query = select(Envelope).where(
        Envelope.budget_id == budget_id,
        Envelope.is_active == True,  # noqa: E712
        Envelope.target_balance.isnot(None),
        Envelope.current_balance >= Envelope.target_balance,
        Envelope.goal_reached_notified_at.is_(None),
    )

    result = await session.execute(query)
    envelopes = result.scalars().all()

    new_notifications = []
    for envelope in envelopes:
        balance_dollars = envelope.current_balance / 100
        target_dollars = (envelope.target_balance or 0) / 100

        notification = Notification(
            id=uuid7(),
            budget_id=budget_id,
            user_id=None,
            notification_type=NotificationType.GOAL_REACHED,
            title=f"Goal reached: {envelope.name}",
            message=f"{envelope.name} has reached its ${target_dollars:.2f} target! Current balance: ${balance_dollars:.2f}.",
            related_entity_type="envelope",
            related_entity_id=envelope.id,
        )
        session.add(notification)
        new_notifications.append(notification)

        # Mark envelope as notified
        envelope.goal_reached_notified_at = now

    return new_notifications


async def _get_recent_notification(
    session: AsyncSession,
    budget_id: UUID,
    notification_type: NotificationType,
    entity_type: str,
    entity_id: UUID,
) -> Notification | None:
    """Check if a recent unread/undismissed notification exists for this entity."""
    query = select(Notification).where(
        Notification.budget_id == budget_id,
        Notification.notification_type == notification_type,
        Notification.related_entity_type == entity_type,
        Notification.related_entity_id == entity_id,
        Notification.is_dismissed == False,  # noqa: E712
    )

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def cleanup_old_notifications(
    session: AsyncSession,
    budget_id: UUID,
    days_to_keep: int = 30,
) -> int:
    """Delete old dismissed notifications.

    Args:
        session: Database session
        budget_id: Budget to clean up
        days_to_keep: Keep dismissed notifications for this many days (not yet implemented)

    Returns:
        Number of notifications deleted
    """
    # TODO: Use UUID7 timestamp or created_at to filter by age
    # For now, delete all dismissed notifications
    _ = days_to_keep  # Unused for now, suppress lint warning
    stmt = delete(Notification).where(
        Notification.budget_id == budget_id,
        Notification.is_dismissed == True,  # noqa: E712
    )

    result = await session.execute(stmt)
    return result.rowcount
