from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User


async def test_income_vs_expenses_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic income vs expenses aggregation."""
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
    session.add_all([account, payee])
    await session.flush()

    # Create income and expense transactions in the same month
    today = date.today()
    first_of_month = today.replace(day=1)

    # Income: +5000
    income_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=first_of_month,
        amount=500000,  # $5000
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Expense: -3000
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=first_of_month + timedelta(days=5),
        amount=-300000,  # -$3000
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([income_txn, expense_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_income"] == 500000
    assert data["total_expenses"] == 300000
    assert data["total_net"] == 200000

    assert len(data["periods"]) == 1
    period = data["periods"][0]
    assert period["period_start"] == str(first_of_month)
    assert period["income"] == 500000
    assert period["expenses"] == 300000
    assert period["net"] == 200000
    assert period["transaction_count"] == 2


async def test_income_vs_expenses_multiple_months(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test aggregation across multiple months."""
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
    session.add_all([account, payee])
    await session.flush()

    # Create transactions in two different months
    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    # January: +5000, -2000
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=500000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-200000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # February: +4000, -4500 (deficit)
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=feb,
        amount=400000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    txn4 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=feb,
        amount=-450000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([txn1, txn2, txn3, txn4])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # Totals across all months
    assert data["total_income"] == 900000  # 5000 + 4000
    assert data["total_expenses"] == 650000  # 2000 + 4500
    assert data["total_net"] == 250000  # 3000 - 500

    # Should be ordered most recent first
    assert len(data["periods"]) == 2
    assert data["periods"][0]["period_start"] == "2024-02-01"
    assert data["periods"][0]["income"] == 400000
    assert data["periods"][0]["expenses"] == 450000
    assert data["periods"][0]["net"] == -50000  # Deficit

    assert data["periods"][1]["period_start"] == "2024-01-01"
    assert data["periods"][1]["income"] == 500000
    assert data["periods"][1]["expenses"] == 200000
    assert data["periods"][1]["net"] == 300000  # Surplus


async def test_income_vs_expenses_excludes_transfers(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transfer transactions are excluded."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account1 = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    account2 = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([account1, account2, payee])
    await session.flush()

    today = date.today().replace(day=1)

    # Regular transaction
    regular_txn = Transaction(
        budget_id=budget.id,
        account_id=account1.id,
        payee_id=payee.id,
        date=today,
        amount=-100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Internal transfer between budget accounts (should be excluded)
    transfer_out = Transaction(
        budget_id=budget.id,
        account_id=account1.id,
        date=today,
        amount=-50000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    transfer_in = Transaction(
        budget_id=budget.id,
        account_id=account2.id,
        date=today,
        amount=50000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    session.add_all([regular_txn, transfer_out, transfer_in])
    await session.flush()

    # Link the transfers
    transfer_out.linked_transaction_id = transfer_in.id
    transfer_in.linked_transaction_id = transfer_out.id
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the regular transaction should be counted, not the internal transfer
    assert data["total_expenses"] == 100000
    assert len(data["periods"]) == 1
    assert data["periods"][0]["transaction_count"] == 1


async def test_income_vs_expenses_excludes_non_budget_accounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transactions from non-budget accounts are excluded."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    budget_account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    non_budget_account = Account(
        budget_id=budget.id,
        name="Tracking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([budget_account, non_budget_account, payee])
    await session.flush()

    today = date.today().replace(day=1)

    # Transaction in budget account
    budget_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        payee_id=payee.id,
        date=today,
        amount=-100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Transaction in non-budget account (should be excluded)
    non_budget_txn = Transaction(
        budget_id=budget.id,
        account_id=non_budget_account.id,
        payee_id=payee.id,
        date=today,
        amount=-200000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([budget_txn, non_budget_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the budget account transaction should be counted
    assert data["total_expenses"] == 100000


async def test_income_vs_expenses_excludes_scheduled(
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
    session.add_all([account, payee])
    await session.flush()

    today = date.today().replace(day=1)

    # Posted transaction
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Scheduled transaction (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today + timedelta(days=30),
        amount=-200000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([posted_txn, scheduled_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the posted transaction should be counted
    assert data["total_expenses"] == 100000


async def test_income_vs_expenses_date_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test date range filtering."""
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
    session.add_all([account, payee])
    await session.flush()

    # Create transactions in different months
    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    txn_jan = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=jan,
        amount=-100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    txn_feb = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=feb,
        amount=-200000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([txn_jan, txn_feb])
    await session.flush()

    # Filter to January only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-31"
    assert data["total_expenses"] == 100000
    assert len(data["periods"]) == 1


async def test_income_vs_expenses_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no transactions."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_income"] == 0
    assert data["total_expenses"] == 0
    assert data["total_net"] == 0
    assert data["periods"] == []


async def test_income_vs_expenses_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 403


async def test_income_vs_expenses_excludes_adjustment_transactions(
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
    session.add_all([account, payee])
    await session.flush()

    today = date.today().replace(day=1)

    # Regular income transaction (should be included)
    regular_income_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Regular expense transaction (should be included)
    regular_expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-50000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Adjustment income (e.g., starting balance) - should be excluded
    adjustment_income_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=today,
        amount=1000000,  # Large positive amount (initial balance)
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
        memo="Starting balance",
    )
    # Adjustment expense (e.g., credit card initial balance) - should be excluded
    adjustment_expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=today,
        amount=-500000,  # Large negative amount
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
        memo="Credit card balance",
    )
    session.add_all(
        [
            regular_income_txn,
            regular_expense_txn,
            adjustment_income_txn,
            adjustment_expense_txn,
        ]
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # Only regular transactions should be counted, not adjustments
    assert data["total_income"] == 100000  # Not 1100000
    assert data["total_expenses"] == 50000  # Not 550000
    assert data["total_net"] == 50000  # Not -400000
    assert len(data["periods"]) == 1
    assert data["periods"][0]["transaction_count"] == 2  # Not 4


async def test_income_vs_expenses_includes_transfers_to_tracking(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transfers to/from tracking accounts ARE included."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    investment = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,  # Tracking account
    )
    session.add_all([checking, investment])
    await session.flush()

    today = date.today().replace(day=1)

    # Transfer: checking → investment (budget → tracking)
    # This SHOULD be counted as an expense - money leaving the budget
    transfer_out = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=today,
        amount=-25000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    transfer_in = Transaction(
        budget_id=budget.id,
        account_id=investment.id,
        date=today,
        amount=25000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    session.add_all([transfer_out, transfer_in])
    await session.flush()

    # Link the transfers
    transfer_out.linked_transaction_id = transfer_in.id
    transfer_in.linked_transaction_id = transfer_out.id
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # The transfer to tracking should count as an expense
    assert data["total_income"] == 0
    assert data["total_expenses"] == 25000
    assert data["total_net"] == -25000
    assert len(data["periods"]) == 1
    assert data["periods"][0]["transaction_count"] == 1


async def test_income_vs_expenses_includes_transfers_from_tracking(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transfers FROM tracking accounts ARE included as income."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    investment = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,  # Tracking account
    )
    session.add_all([checking, investment])
    await session.flush()

    today = date.today().replace(day=1)

    # Transfer: investment → checking (tracking → budget)
    # This SHOULD be counted as income - money entering the budget
    transfer_out = Transaction(
        budget_id=budget.id,
        account_id=investment.id,
        date=today,
        amount=-30000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    transfer_in = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=today,
        amount=30000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    session.add_all([transfer_out, transfer_in])
    await session.flush()

    # Link the transfers
    transfer_out.linked_transaction_id = transfer_in.id
    transfer_in.linked_transaction_id = transfer_out.id
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/income-vs-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    # The transfer from tracking should count as income
    assert data["total_income"] == 30000
    assert data["total_expenses"] == 0
    assert data["total_net"] == 30000
    assert len(data["periods"]) == 1
    assert data["periods"][0]["transaction_count"] == 1
