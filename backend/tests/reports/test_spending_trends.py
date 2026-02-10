from datetime import date
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


async def test_spending_trends_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic spending trends report."""
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
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create spending in January and February 2024
    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    for txn_date, amount in [(jan, -10000), (jan, -15000), (feb, -20000)]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=txn_date,
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
                date=txn_date,
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-02-29"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-02-29"
    assert data["period_count"] == 2

    assert len(data["envelopes"]) == 1
    envelope_data = data["envelopes"][0]
    assert envelope_data["envelope_name"] == "Groceries"
    assert envelope_data["total_spent"] == 45000  # $100 + $150 + $200
    assert envelope_data["average_per_period"] == 22500  # $450 / 2 months

    # Check periods
    assert len(envelope_data["periods"]) == 2
    jan_period = envelope_data["periods"][0]
    assert jan_period["period_start"] == "2024-01-01"
    assert jan_period["amount"] == 25000  # $100 + $150
    assert jan_period["transaction_count"] == 2

    feb_period = envelope_data["periods"][1]
    assert feb_period["period_start"] == "2024-02-01"
    assert feb_period["amount"] == 20000
    assert feb_period["transaction_count"] == 1


async def test_spending_trends_multiple_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test trends across multiple envelopes sorted by total spent."""
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
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    gas = Envelope(budget_id=budget.id, name="Gas", current_balance=0)
    dining = Envelope(budget_id=budget.id, name="Dining", current_balance=0)
    session.add_all([account, payee, groceries, gas, dining])
    await session.flush()

    jan = date(2024, 1, 15)

    # Groceries: $500, Gas: $200, Dining: $300
    spending = [
        (groceries.id, -50000),
        (gas.id, -20000),
        (dining.id, -30000),
    ]

    for envelope_id, amount in spending:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=jan,
            amount=amount,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()
        session.add(
            Allocation(
                budget_id=budget.id,
                envelope_id=envelope_id,
                transaction_id=txn.id,
                group_id=uuid7(),
                amount=amount,
                date=jan,
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by total spent (descending)
    assert len(data["envelopes"]) == 3
    assert data["envelopes"][0]["envelope_name"] == "Groceries"
    assert data["envelopes"][0]["total_spent"] == 50000
    assert data["envelopes"][1]["envelope_name"] == "Dining"
    assert data["envelopes"][1]["total_spent"] == 30000
    assert data["envelopes"][2]["envelope_name"] == "Gas"
    assert data["envelopes"][2]["total_spent"] == 20000


async def test_spending_trends_fills_empty_months(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that months with no spending show zero."""
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
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Only spend in January, skip February
    jan = date(2024, 1, 15)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-10000,
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
            amount=-10000,
            date=jan,
        )
    )
    await session.flush()

    # Query for Jan-Feb
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-02-29"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["period_count"] == 2
    envelope_data = data["envelopes"][0]

    # January should have spending
    assert envelope_data["periods"][0]["period_start"] == "2024-01-01"
    assert envelope_data["periods"][0]["amount"] == 10000

    # February should be zero
    assert envelope_data["periods"][1]["period_start"] == "2024-02-01"
    assert envelope_data["periods"][1]["amount"] == 0
    assert envelope_data["periods"][1]["transaction_count"] == 0


async def test_spending_trends_filter_by_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering to specific envelopes."""
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
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    gas = Envelope(budget_id=budget.id, name="Gas", current_balance=0)
    session.add_all([account, payee, groceries, gas])
    await session.flush()

    jan = date(2024, 1, 15)

    for envelope in [groceries, gas]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=jan,
            amount=-10000,
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
                amount=-10000,
                date=jan,
            )
        )
    await session.flush()

    # Filter to groceries only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "envelope_id": str(groceries.id),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["envelopes"]) == 1
    assert data["envelopes"][0]["envelope_name"] == "Groceries"


async def test_spending_trends_excludes_income(
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
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    jan = date(2024, 1, 15)

    # Spending
    spend_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-10000,
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
            amount=-10000,
            date=jan,
        )
    )

    # Refund (should be excluded)
    refund_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=5000,
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
            amount=5000,
            date=jan,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    # Only spending should be counted
    assert data["envelopes"][0]["total_spent"] == 10000


async def test_spending_trends_excludes_scheduled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scheduled transactions are excluded."""
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
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    jan = date(2024, 1, 15)

    # Posted
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-10000,
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
            amount=-10000,
            date=jan,
        )
    )

    # Scheduled (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-20000,
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
            amount=-20000,
            date=jan,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    # Only posted should be counted
    assert data["envelopes"][0]["total_spent"] == 10000


async def test_spending_trends_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no spending data."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["period_count"] == 1
    assert data["envelopes"] == []


async def test_spending_trends_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/spending-trends",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 403
