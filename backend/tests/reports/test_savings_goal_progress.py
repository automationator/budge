from datetime import date, timedelta
from uuid import uuid7

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus
from src.users.models import User


async def test_savings_goal_progress_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic savings goal progress report."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    # Goal: $10,000, current: $5,000 (50%)
    envelope = Envelope(
        budget_id=budget.id,
        name="Emergency Fund",
        current_balance=500000,
        target_balance=1000000,
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["calculation_period_days"] == 90
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["envelope_name"] == "Emergency Fund"
    assert item["target_balance"] == 1000000
    assert item["current_balance"] == 500000
    assert item["progress_percent"] == 50
    assert item["remaining"] == 500000


async def test_savings_goal_progress_with_contributions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that monthly contribution rate and ETA are calculated."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    # Goal: $10,000, current: $5,000
    envelope = Envelope(
        budget_id=budget.id,
        name="Emergency Fund",
        current_balance=500000,
        target_balance=1000000,
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create contributions over the last 90 days
    # $1000 total over 90 days = ~$333/month
    today = date.today()
    for i in range(3):
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i * 30),
            amount=100000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()
        session.add(
            Allocation(
                budget_id=budget.id,
                envelope_id=envelope.id,
                transaction_id=txn.id,
                group_id=uuid7(),
                amount=33333,  # $333 contribution
                date=txn.date,
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    item = data["items"][0]
    assert item["monthly_contribution_rate"] > 0
    assert item["estimated_months_to_goal"] is not None
    # With ~$333/month and $5000 remaining, should be ~15 months
    assert item["estimated_months_to_goal"] > 0


async def test_savings_goal_progress_multiple_goals(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test multiple goals sorted by progress."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # 80% progress
    goal1 = Envelope(
        budget_id=budget.id,
        name="Vacation",
        current_balance=800000,
        target_balance=1000000,
    )
    # 50% progress
    goal2 = Envelope(
        budget_id=budget.id,
        name="Emergency Fund",
        current_balance=500000,
        target_balance=1000000,
    )
    # 25% progress
    goal3 = Envelope(
        budget_id=budget.id,
        name="New Car",
        current_balance=250000,
        target_balance=1000000,
    )
    session.add_all([goal1, goal2, goal3])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by progress percent descending
    assert len(data["items"]) == 3
    assert data["items"][0]["envelope_name"] == "Vacation"
    assert data["items"][0]["progress_percent"] == 80
    assert data["items"][1]["envelope_name"] == "Emergency Fund"
    assert data["items"][1]["progress_percent"] == 50
    assert data["items"][2]["envelope_name"] == "New Car"
    assert data["items"][2]["progress_percent"] == 25


async def test_savings_goal_progress_goal_reached(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test goal that has been reached."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Over the target
    envelope = Envelope(
        budget_id=budget.id,
        name="Completed Goal",
        current_balance=1200000,  # $12,000
        target_balance=1000000,  # $10,000
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    item = data["items"][0]
    assert item["progress_percent"] == 100
    assert item["remaining"] == 0
    assert item["estimated_months_to_goal"] == 0


async def test_savings_goal_progress_no_contributions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test goal with no contribution history."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="New Goal",
        current_balance=0,
        target_balance=1000000,
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    item = data["items"][0]
    assert item["monthly_contribution_rate"] == 0
    assert item["estimated_months_to_goal"] is None  # Can't estimate


async def test_savings_goal_progress_excludes_non_goals(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that envelopes without target_balance are excluded."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Has target - should be included
    goal = Envelope(
        budget_id=budget.id,
        name="Goal",
        current_balance=500000,
        target_balance=1000000,
    )
    # No target - should be excluded
    regular = Envelope(
        budget_id=budget.id,
        name="Regular",
        current_balance=500000,
        target_balance=None,
    )
    # Zero target - should be excluded
    zero_target = Envelope(
        budget_id=budget.id,
        name="Zero Target",
        current_balance=500000,
        target_balance=0,
    )
    session.add_all([goal, regular, zero_target])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["envelope_name"] == "Goal"


async def test_savings_goal_progress_custom_period(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test custom calculation period."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Goal",
        current_balance=500000,
        target_balance=1000000,
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress",
        params={"calculation_period_days": 180},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["calculation_period_days"] == 180


async def test_savings_goal_progress_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no savings goals."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_savings_goal_progress_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' reports."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/savings-goal-progress"
    )
    assert response.status_code == 403
