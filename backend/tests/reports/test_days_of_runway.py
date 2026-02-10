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
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User


async def test_days_of_runway_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic days of runway calculation."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    # Envelope with $300 balance
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=30000)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create spending transactions over the last 30 days
    # Spend $10/day for 30 days = $300 total, avg $10/day
    today = date.today()
    for i in range(30):
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i),
            amount=-1000,  # -$10
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()

        alloc = Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn.id,
            group_id=uuid7(),
            amount=-1000,
            date=txn.date,
        )
        session.add(alloc)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["calculation_period_days"] == 30
    assert data["total_balance"] == 30000  # $300
    assert data["total_average_daily_spending"] == 1000  # $10/day
    assert data["total_days_of_runway"] == 30  # $300 / $10/day = 30 days

    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["envelope_name"] == "Groceries"
    assert item["current_balance"] == 30000
    assert item["average_daily_spending"] == 1000
    assert item["days_of_runway"] == 30


async def test_days_of_runway_multiple_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test runway calculation across multiple envelopes."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    # Groceries: $100 balance, $10/day spending = 10 days runway
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    # Gas: $200 balance, $5/day spending = 40 days runway
    gas = Envelope(budget_id=budget.id, name="Gas", current_balance=20000)
    session.add_all([account, payee, groceries, gas])
    await session.flush()

    today = date.today()
    # Groceries: $300 spending over 30 days = $10/day
    for i in range(30):
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i),
            amount=-1000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()
        session.add(
            Allocation(
                budget_id=budget.id,
                envelope_id=groceries.id,
                transaction_id=txn.id,
                group_id=uuid7(),
                amount=-1000,
                date=txn.date,
            )
        )

    # Gas: $150 spending over 30 days = $5/day
    for i in range(0, 30, 2):  # Every other day
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i),
            amount=-1000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()
        session.add(
            Allocation(
                budget_id=budget.id,
                envelope_id=gas.id,
                transaction_id=txn.id,
                group_id=uuid7(),
                amount=-1000,
                date=txn.date,
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    # Total: $300 balance, $15/day spending = 20 days runway
    assert data["total_balance"] == 30000
    assert data["total_average_daily_spending"] == 1500  # $15/day (10 + 5)
    assert data["total_days_of_runway"] == 20  # $300 / $15 = 20

    # Items should be sorted by runway (ascending, None at end)
    assert len(data["items"]) == 2
    assert data["items"][0]["envelope_name"] == "Groceries"
    assert data["items"][0]["days_of_runway"] == 10
    assert data["items"][1]["envelope_name"] == "Gas"
    assert data["items"][1]["days_of_runway"] == 40


async def test_days_of_runway_no_spending(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test when envelope has no spending history."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Envelope with balance but no spending
    envelope = Envelope(budget_id=budget.id, name="Emergency", current_balance=100000)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_balance"] == 100000
    assert data["total_average_daily_spending"] == 0
    assert data["total_days_of_runway"] is None  # No spending to calculate runway

    assert len(data["items"]) == 1
    assert data["items"][0]["average_daily_spending"] == 0
    assert data["items"][0]["days_of_runway"] is None


async def test_days_of_runway_exclude_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test excluding specific envelopes from calculation."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    emergency = Envelope(
        budget_id=budget.id, name="Emergency Fund", current_balance=500000
    )
    session.add_all([account, payee, groceries, emergency])
    await session.flush()

    # Add spending to groceries
    today = date.today()
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=groceries.id,
            transaction_id=txn.id,
            group_id=uuid7(),
            amount=-3000,
            date=today,
        )
    )
    await session.flush()

    # Exclude emergency fund
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway",
        params={"exclude_envelope_id": str(emergency.id)},
    )
    assert response.status_code == 200
    data = response.json()

    # Only groceries should be included
    assert data["total_balance"] == 10000
    assert len(data["items"]) == 1
    assert data["items"][0]["envelope_name"] == "Groceries"


async def test_days_of_runway_custom_period(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test custom calculation period."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()
    # Create spending: $10 yesterday, $20 two days ago
    # With 7 day period: $30 / 7 = $4/day
    for i, amount in [(1, -1000), (2, -2000)]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i),
            amount=amount,
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
                amount=amount,
                date=txn.date,
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway",
        params={"calculation_period_days": 7},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["calculation_period_days"] == 7
    # $30 spending / 7 days = ~$4.28/day, integer division = $4/day
    assert data["total_average_daily_spending"] == 428  # 3000 / 7 = 428
    # $100 / $4.28/day = 23 days
    assert data["total_days_of_runway"] == 23


async def test_days_of_runway_excludes_scheduled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scheduled transactions are excluded from spending calculation."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()
    # Posted transaction
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add(posted_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=posted_txn.id,
            group_id=uuid7(),
            amount=-3000,
            date=today,
        )
    )

    # Scheduled transaction (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today + timedelta(days=7),
        amount=-5000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(scheduled_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=scheduled_txn.id,
            group_id=uuid7(),
            amount=-5000,
            date=scheduled_txn.date,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    # Only posted transaction should be counted
    # $30 spending / 30 days = $1/day
    assert data["total_average_daily_spending"] == 100


async def test_days_of_runway_excludes_income(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that positive allocations (income/refunds) are excluded."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()
    # Spending transaction
    spend_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add(spend_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=spend_txn.id,
            group_id=uuid7(),
            amount=-3000,
            date=today,
        )
    )

    # Refund/income transaction (should be excluded from spending calculation)
    refund_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=1000,
        status=TransactionStatus.POSTED,
    )
    session.add(refund_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=refund_txn.id,
            group_id=uuid7(),
            amount=1000,
            date=today,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    # Only spending ($30) should be counted, not the refund
    assert data["total_average_daily_spending"] == 100  # $30 / 30 days


async def test_days_of_runway_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no envelopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_balance"] == 0
    assert data["total_average_daily_spending"] == 0
    assert data["total_days_of_runway"] is None
    assert data["items"] == []


async def test_days_of_runway_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 403


async def test_days_of_runway_excludes_adjustment_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that ADJUSTMENT transactions (e.g., initial balances) are excluded."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=10000)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()

    # Normal STANDARD spending transaction (should be included)
    standard_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,  # -$30
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add(standard_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=standard_txn.id,
            group_id=uuid7(),
            amount=-3000,
            date=today,
        )
    )

    # ADJUSTMENT transaction (e.g., initial balance - should be excluded)
    adjustment_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=today,
        amount=-100000,  # -$1000 - large amount to make it obvious if included
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
        memo="Starting balance",
    )
    session.add(adjustment_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=adjustment_txn.id,
            group_id=uuid7(),
            amount=-100000,
            date=today,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/days-of-runway"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the standard transaction spending should be counted ($30/30 days = $1/day)
    # NOT the adjustment ($1000 which would make it $1030/30 = ~$34/day)
    assert data["total_average_daily_spending"] == 100  # $1/day, not $34/day
    assert len(data["items"]) == 1
    assert data["items"][0]["average_daily_spending"] == 100  # $1/day
