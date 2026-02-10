from datetime import date, timedelta
from uuid import uuid4

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


async def test_envelope_balance_history_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic envelope balance history calculation."""
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

    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # Create transactions on different days
    from uuid import uuid7

    # Day 1: +5000
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=two_days_ago,
        amount=5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()

    alloc1 = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn1.id,
        group_id=uuid7(),
        amount=5000,
        date=two_days_ago,
    )
    session.add(alloc1)

    # Day 2: -2000
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=yesterday,
        amount=-2000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()

    alloc2 = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn2.id,
        group_id=uuid7(),
        amount=-2000,
        date=yesterday,
    )
    session.add(alloc2)

    # Day 3: -1000
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-1000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn3)
    await session.flush()

    alloc3 = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn3.id,
        group_id=uuid7(),
        amount=-1000,
        date=today,
    )
    session.add(alloc3)
    await session.flush()

    # Query the history
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(two_days_ago),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["envelope_id"] == str(envelope.id)
    assert data["envelope_name"] == "Groceries"
    assert len(data["items"]) == 3

    # Check daily balances
    items = data["items"]
    assert items[0]["date"] == str(two_days_ago)
    assert items[0]["balance"] == 5000  # +5000

    assert items[1]["date"] == str(yesterday)
    assert items[1]["balance"] == 3000  # 5000 - 2000

    assert items[2]["date"] == str(today)
    assert items[2]["balance"] == 2000  # 3000 - 1000


async def test_envelope_balance_history_starting_balance(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that allocations before start_date are included in starting balance."""
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
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()
    last_week = today - timedelta(days=7)

    from uuid import uuid7

    # Create an allocation from last week
    txn_old = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=last_week,
        amount=10000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn_old)
    await session.flush()

    alloc_old = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn_old.id,
        group_id=uuid7(),
        amount=10000,
        date=last_week,
    )
    session.add(alloc_old)
    await session.flush()

    # Query starting from yesterday (after the old allocation)
    yesterday = today - timedelta(days=1)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(yesterday),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Starting balance should include the old allocation
    assert len(data["items"]) == 2
    assert data["items"][0]["date"] == str(yesterday)
    assert data["items"][0]["balance"] == 10000  # Includes pre-start allocation
    assert data["items"][1]["date"] == str(today)
    assert data["items"][1]["balance"] == 10000


async def test_envelope_balance_history_empty_days(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that days without activity carry forward the previous balance."""
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
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    today = date.today()
    five_days_ago = today - timedelta(days=5)

    from uuid import uuid7

    # Create allocation only on day 1
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=five_days_ago,
        amount=5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn)
    await session.flush()

    alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn.id,
        group_id=uuid7(),
        amount=5000,
        date=five_days_ago,
    )
    session.add(alloc)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(five_days_ago),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Should have 6 days of data (5 days ago through today)
    assert len(data["items"]) == 6

    # All days should show balance of 5000 (carried forward)
    for item in data["items"]:
        assert item["balance"] == 5000


async def test_envelope_balance_history_no_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test envelope with no allocations returns zero balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Empty", current_balance=0)
    session.add(envelope)
    await session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(yesterday),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 2
    assert data["items"][0]["balance"] == 0
    assert data["items"][1]["balance"] == 0


async def test_envelope_balance_history_includes_metadata(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that response includes envelope metadata."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Savings Goal",
        current_balance=5000,
        target_balance=10000,
    )
    session.add(envelope)
    await session.flush()

    today = date.today()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["envelope_id"] == str(envelope.id)
    assert data["envelope_name"] == "Savings Goal"
    assert data["current_balance"] == 5000
    assert data["target_balance"] == 10000
    assert data["start_date"] == str(today)
    assert data["end_date"] == str(today)


async def test_envelope_balance_history_envelope_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that non-existent envelope returns 404."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    fake_id = uuid4()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(fake_id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 404


async def test_envelope_balance_history_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' envelope history."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    envelope = Envelope(budget_id=other_budget.id, name="Other", current_balance=0)
    session.add(envelope)
    await session.flush()

    today = date.today()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(envelope.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 403


async def test_envelope_balance_history_wrong_budget_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that envelope from different budget returns 404 even with valid budget."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    my_budget = result.scalar_one()

    result2 = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result2.scalar_one()

    # Create envelope in other budget
    other_envelope = Envelope(
        budget_id=other_budget.id, name="Other", current_balance=0
    )
    session.add(other_envelope)
    await session.flush()

    today = date.today()

    # Try to access other budget's envelope via my budget
    response = await authenticated_client.get(
        f"/api/v1/budgets/{my_budget.id}/reports/envelope-balance-history",
        params={
            "envelope_id": str(other_envelope.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 404
