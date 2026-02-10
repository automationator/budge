"""Tests for the notifications module."""

from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.notifications import service
from src.notifications.models import (
    Notification,
    NotificationType,
)
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.transactions.models import Transaction, TransactionStatus
from src.users.models import User


async def test_list_notifications_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test listing notifications when there are none."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/notifications"
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_get_notification_count_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test getting notification count when there are none."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/notifications/count"
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0


async def test_generate_low_balance_notification(
    authenticated_client: AsyncClient,  # noqa: ARG001
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test generating a low balance notification."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope with low balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Test Envelope",
        current_balance=-500,  # Negative balance
    )
    session.add(envelope)
    await session.flush()

    # Set up preference with threshold
    pref = await service.get_or_create_preference(
        session, budget.id, test_user.id, NotificationType.LOW_BALANCE
    )
    pref.low_balance_threshold = 0

    # Generate notifications
    new_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )

    # Should have at least one low balance notification
    low_balance = [
        n
        for n in new_notifications
        if n.notification_type == NotificationType.LOW_BALANCE
    ]
    assert len(low_balance) >= 1
    assert low_balance[0].related_entity_id == envelope.id
    assert "Test Envelope" in low_balance[0].title


async def test_generate_goal_reached_notification(
    authenticated_client: AsyncClient,  # noqa: ARG001
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test generating a goal reached notification."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope that has reached its goal
    envelope = Envelope(
        budget_id=budget.id,
        name="Savings Goal",
        current_balance=150000,  # $1500
        target_balance=100000,  # $1000 goal
        goal_reached_notified_at=None,  # Not yet notified
    )
    session.add(envelope)
    await session.flush()

    # Generate notifications
    new_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )

    # Should have a goal reached notification
    goal_reached = [
        n
        for n in new_notifications
        if n.notification_type == NotificationType.GOAL_REACHED
    ]
    assert len(goal_reached) == 1
    assert goal_reached[0].related_entity_id == envelope.id
    assert "Savings Goal" in goal_reached[0].title

    # Envelope should now be marked as notified
    await session.refresh(envelope)
    assert envelope.goal_reached_notified_at is not None


async def test_goal_reached_not_duplicated(
    authenticated_client: AsyncClient,  # noqa: ARG001
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that goal reached notifications are not duplicated."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope that has reached its goal
    envelope = Envelope(
        budget_id=budget.id,
        name="Already Notified",
        current_balance=150000,
        target_balance=100000,
        goal_reached_notified_at=None,
    )
    session.add(envelope)
    await session.flush()

    # Generate notifications first time
    first_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )
    goal_reached_first = [
        n
        for n in first_notifications
        if n.notification_type == NotificationType.GOAL_REACHED
    ]
    assert len(goal_reached_first) == 1

    # Generate again - should not create duplicate
    second_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )
    goal_reached_second = [
        n
        for n in second_notifications
        if n.notification_type == NotificationType.GOAL_REACHED
    ]
    assert len(goal_reached_second) == 0


async def test_generate_upcoming_expense_notification(
    authenticated_client: AsyncClient,  # noqa: ARG001
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test generating an upcoming expense notification for underfunded expense."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(account)

    # Create envelope with insufficient balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Bills",
        current_balance=5000,  # $50
    )
    session.add(envelope)

    # Create payee
    payee = Payee(
        budget_id=budget.id,
        name="Electric Company",
    )
    session.add(payee)
    await session.flush()

    # Create recurring transaction
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        envelope_id=envelope.id,
        payee_id=payee.id,
        amount=-15000,  # $150 expense
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=3),
    )
    session.add(recurring)
    await session.flush()

    # Create scheduled transaction
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        recurring_transaction_id=recurring.id,
        date=date.today() + timedelta(days=3),
        amount=-15000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(transaction)
    await session.flush()

    # Set preference for 7 days ahead
    pref = await service.get_or_create_preference(
        session, budget.id, test_user.id, NotificationType.UPCOMING_EXPENSE
    )
    pref.upcoming_expense_days = 7

    # Generate notifications
    new_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )

    # Should have an upcoming expense notification
    upcoming = [
        n
        for n in new_notifications
        if n.notification_type == NotificationType.UPCOMING_EXPENSE
    ]
    assert len(upcoming) >= 1


async def test_generate_recurring_not_funded_notification(
    authenticated_client: AsyncClient,  # noqa: ARG001
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test generating a recurring not funded notification."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(account)

    # Create envelope with insufficient balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Rent",
        current_balance=50000,  # $500
    )
    session.add(envelope)

    # Create payee
    payee = Payee(
        budget_id=budget.id,
        name="Landlord",
    )
    session.add(payee)
    await session.flush()

    # Create recurring transaction that's underfunded
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        envelope_id=envelope.id,
        payee_id=payee.id,
        amount=-100000,  # $1000 expense
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=15),
        is_active=True,
    )
    session.add(recurring)
    await session.flush()

    # Generate notifications
    new_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )

    # Should have a recurring not funded notification
    not_funded = [
        n
        for n in new_notifications
        if n.notification_type == NotificationType.RECURRING_NOT_FUNDED
    ]
    assert len(not_funded) >= 1
    assert not_funded[0].related_entity_id == recurring.id


async def test_mark_notifications_read(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test marking notifications as read."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a notification
    notification = Notification(
        budget_id=budget.id,
        user_id=None,
        notification_type=NotificationType.LOW_BALANCE,
        title="Test notification",
        message="Test message",
        is_read=False,
    )
    session.add(notification)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/notifications/mark-read",
        json={"notification_ids": [str(notification.id)]},
    )
    assert response.status_code == 204

    # Verify notification is marked as read
    await session.refresh(notification)
    assert notification.is_read is True


async def test_mark_notifications_dismissed(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test marking notifications as dismissed."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a notification
    notification = Notification(
        budget_id=budget.id,
        user_id=None,
        notification_type=NotificationType.GOAL_REACHED,
        title="Test notification",
        message="Test message",
        is_dismissed=False,
    )
    session.add(notification)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/notifications/mark-dismissed",
        json={"notification_ids": [str(notification.id)]},
    )
    assert response.status_code == 204

    # Verify notification is marked as dismissed
    await session.refresh(notification)
    assert notification.is_dismissed is True


async def test_list_preferences(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test listing notification preferences creates defaults."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/notifications/preferences"
    )
    assert response.status_code == 200
    data = response.json()

    # Should have preferences for all 4 types
    assert len(data) == 4
    types = {p["notification_type"] for p in data}
    assert types == {
        "low_balance",
        "upcoming_expense",
        "recurring_not_funded",
        "goal_reached",
    }


async def test_update_preference(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test updating a notification preference."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/notifications/preferences/low_balance",
        json={
            "is_enabled": True,
            "low_balance_threshold": 10000,  # $100
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_enabled"] is True
    assert data["low_balance_threshold"] == 10000


async def test_disable_preference(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test disabling a notification type."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope with low balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Disabled Test",
        current_balance=-500,
    )
    session.add(envelope)
    await session.flush()

    # Disable low balance notifications
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/notifications/preferences/low_balance",
        json={"is_enabled": False},
    )
    assert response.status_code == 200

    # Generate notifications - should not create low balance notification
    new_notifications = await service.generate_notifications(
        session, budget.id, test_user.id
    )
    low_balance = [
        n
        for n in new_notifications
        if n.notification_type == NotificationType.LOW_BALANCE
    ]
    assert len(low_balance) == 0


async def test_notifications_require_authentication(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that notification endpoints require authentication."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await client.get(f"/api/v1/budgets/{budget.id}/notifications")
    assert response.status_code == 401


async def test_notifications_require_budget_membership(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users can only see notifications for their budgets."""
    # Get test_user2's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    # test_user (authenticated) should not be able to access other_budget's notifications
    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/notifications"
    )
    assert response.status_code == 403


async def test_dismissed_notifications_excluded_by_default(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that dismissed notifications are excluded by default."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a dismissed notification
    notification = Notification(
        budget_id=budget.id,
        user_id=None,
        notification_type=NotificationType.LOW_BALANCE,
        title="Dismissed notification",
        message="This should be hidden",
        is_dismissed=True,
    )
    session.add(notification)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/notifications"
    )
    assert response.status_code == 200
    data = response.json()

    # Should not include dismissed notification
    ids = [n["id"] for n in data]
    assert str(notification.id) not in ids


async def test_include_dismissed_notifications(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that dismissed notifications can be included if requested."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a dismissed notification
    notification = Notification(
        budget_id=budget.id,
        user_id=None,
        notification_type=NotificationType.LOW_BALANCE,
        title="Dismissed notification",
        message="This should be visible",
        is_dismissed=True,
    )
    session.add(notification)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/notifications",
        params={"include_dismissed": True},
    )
    assert response.status_code == 200
    data = response.json()

    # Should include dismissed notification
    ids = [n["id"] for n in data]
    assert str(notification.id) in ids
