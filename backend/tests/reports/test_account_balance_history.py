from datetime import date, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus
from src.users.models import User


async def test_account_balance_history_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic account balance history calculation."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=0,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([account, payee])
    await session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # Create transactions on different days
    # Day 1: +5000
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=two_days_ago,
        amount=5000,
        status=TransactionStatus.POSTED,
    )
    # Day 2: -2000
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=yesterday,
        amount=-2000,
        status=TransactionStatus.POSTED,
    )
    # Day 3: -1000
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-1000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn1, txn2, txn3])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(two_days_ago),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == str(account.id)
    assert data["account_name"] == "Checking"
    assert len(data["items"]) == 3

    # Check daily balances
    items = data["items"]
    assert items[0]["date"] == str(two_days_ago)
    assert items[0]["balance"] == 5000  # +5000

    assert items[1]["date"] == str(yesterday)
    assert items[1]["balance"] == 3000  # 5000 - 2000

    assert items[2]["date"] == str(today)
    assert items[2]["balance"] == 2000  # 3000 - 1000


async def test_account_balance_history_starting_balance(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transactions before start_date are included in starting balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=0,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([account, payee])
    await session.flush()

    today = date.today()
    last_week = today - timedelta(days=7)

    # Create a transaction from last week
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

    # Query starting from yesterday (after the old transaction)
    yesterday = today - timedelta(days=1)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(yesterday),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Starting balance should include the old transaction
    assert len(data["items"]) == 2
    assert data["items"][0]["date"] == str(yesterday)
    assert data["items"][0]["balance"] == 10000  # Includes pre-start transaction
    assert data["items"][1]["date"] == str(today)
    assert data["items"][1]["balance"] == 10000


async def test_account_balance_history_empty_days(
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
        cleared_balance=0,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([account, payee])
    await session.flush()

    today = date.today()
    five_days_ago = today - timedelta(days=5)

    # Create transaction only on day 1
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

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(five_days_ago),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Should have 6 days of data
    assert len(data["items"]) == 6

    # All days should show balance of 5000 (carried forward)
    for item in data["items"]:
        assert item["balance"] == 5000


async def test_account_balance_history_no_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test account with no transactions returns zero balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Empty",
        account_type=AccountType.CHECKING,
        cleared_balance=0,
    )
    session.add(account)
    await session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(yesterday),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 2
    assert data["items"][0]["balance"] == 0
    assert data["items"][1]["balance"] == 0


async def test_account_balance_history_includes_metadata(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that response includes account metadata."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=5000,
    )
    session.add(account)
    await session.flush()

    today = date.today()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == str(account.id)
    assert data["account_name"] == "Main Checking"
    assert data["current_balance"] == 5000
    assert data["start_date"] == str(today)
    assert data["end_date"] == str(today)


async def test_account_balance_history_excludes_scheduled(
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
        cleared_balance=0,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([account, payee])
    await session.flush()

    today = date.today()

    # Posted transaction
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=5000,
        status=TransactionStatus.POSTED,
    )
    # Scheduled transaction (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today + timedelta(days=7),
        amount=10000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add_all([posted_txn, scheduled_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Only posted transaction should be counted
    assert data["items"][0]["balance"] == 5000


async def test_account_balance_history_account_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that non-existent account returns 404."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    fake_id = uuid4()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/account-balance-history",
        params={
            "account_id": str(fake_id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 404


async def test_account_balance_history_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' account history."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    account = Account(
        budget_id=other_budget.id,
        name="Other",
        account_type=AccountType.CHECKING,
        cleared_balance=0,
    )
    session.add(account)
    await session.flush()

    today = date.today()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/account-balance-history",
        params={
            "account_id": str(account.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 403


async def test_account_balance_history_wrong_budget_account(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that account from different budget returns 404 even with valid budget."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    my_budget = result.scalar_one()

    result2 = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result2.scalar_one()

    # Create account in other budget
    other_account = Account(
        budget_id=other_budget.id,
        name="Other",
        account_type=AccountType.CHECKING,
        cleared_balance=0,
    )
    session.add(other_account)
    await session.flush()

    today = date.today()

    # Try to access other budget's account via my budget
    response = await authenticated_client.get(
        f"/api/v1/budgets/{my_budget.id}/reports/account-balance-history",
        params={
            "account_id": str(other_account.id),
            "start_date": str(today),
            "end_date": str(today),
        },
    )
    assert response.status_code == 404
