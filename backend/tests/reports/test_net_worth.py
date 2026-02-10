from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User


def create_balance_transaction(
    budget_id, account_id, amount: int, txn_date: date | None = None
) -> Transaction:
    """Create a POSTED transaction to establish an account balance."""
    return Transaction(
        budget_id=budget_id,
        account_id=account_id,
        date=txn_date or date.today(),
        amount=amount,
        is_cleared=True,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
        memo="Opening balance",
    )


async def test_net_worth_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic net worth calculation with assets and liabilities."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    # Create asset account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    # Create liability account
    credit_card = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
    )
    session.add_all([checking, credit_card])
    await session.flush()

    # Create transactions to establish balances
    checking_txn = create_balance_transaction(
        budget.id,
        checking.id,
        1000000,
        start_of_month,  # $10,000
    )
    cc_txn = create_balance_transaction(
        budget.id,
        credit_card.id,
        -250000,
        start_of_month,  # -$2,500
    )
    session.add_all([checking_txn, cc_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["current_total_assets"] == 1000000
    assert data["current_total_liabilities"] == 250000  # Positive value
    assert data["current_net_worth"] == 750000  # 10000 - 2500 = 7500

    assert len(data["periods"]) == 1
    period = data["periods"][0]
    assert period["total_assets"] == 1000000
    assert period["total_liabilities"] == 250000
    assert period["net_worth"] == 750000


async def test_net_worth_includes_all_accounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that off-budget accounts are included in net worth."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    # Create budget account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    # Create off-budget account (should still be included in net worth)
    investment = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    session.add_all([checking, investment])
    await session.flush()

    # Create transactions for balances
    checking_txn = create_balance_transaction(
        budget.id, checking.id, 500000, start_of_month
    )
    investment_txn = create_balance_transaction(
        budget.id, investment.id, 2000000, start_of_month
    )
    session.add_all([checking_txn, investment_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Both accounts should be included
    assert data["current_total_assets"] == 2500000  # 5000 + 20000
    assert data["current_net_worth"] == 2500000


async def test_net_worth_excludes_inactive_accounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that inactive (deleted) accounts are excluded."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    # Create active account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        is_active=True,
    )
    # Create inactive account (should NOT be included)
    old_savings = Account(
        budget_id=budget.id,
        name="Old Savings",
        account_type=AccountType.SAVINGS,
        is_active=False,
    )
    session.add_all([checking, old_savings])
    await session.flush()

    # Create transactions (even for inactive account, to ensure it's filtered by is_active)
    checking_txn = create_balance_transaction(
        budget.id, checking.id, 500000, start_of_month
    )
    old_savings_txn = create_balance_transaction(
        budget.id, old_savings.id, 1000000, start_of_month
    )
    session.add_all([checking_txn, old_savings_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Only active account should be included
    assert data["current_total_assets"] == 500000
    assert len(data["periods"][0]["accounts"]) == 1


async def test_net_worth_historical_balance(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that historical balances are calculated correctly by subtracting future transactions."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(days=1)

    # Create account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(checking)
    await session.flush()

    # Create opening balance transaction in last month = $7,000
    opening_txn = create_balance_transaction(budget.id, checking.id, 700000, last_month)
    # Add a deposit transaction today (this month) = +$3,000 (total now $10,000)
    deposit_txn = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=today,
        amount=300000,  # +$3,000
        is_cleared=True,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([opening_txn, deposit_txn])
    await session.flush()

    # Query for last month should show balance WITHOUT today's transaction
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(last_month),
            "end_date": str(last_month_end),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["periods"]) == 1
    # Historical balance should be $7,000 (just the opening balance, deposit is this month)
    assert data["periods"][0]["total_assets"] == 700000


async def test_net_worth_assets_vs_liabilities_classification(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test correct classification of account types as assets or liabilities."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    # Create one of each account type
    accounts_data = [
        ("Checking", AccountType.CHECKING, 100000),
        ("Savings", AccountType.SAVINGS, 200000),
        ("Money Market", AccountType.MONEY_MARKET, 300000),
        ("Cash", AccountType.CASH, 50000),
        ("Investment", AccountType.INVESTMENT, 500000),
        ("Other", AccountType.OTHER, 25000),
        # Liabilities
        ("Credit Card", AccountType.CREDIT_CARD, -100000),
        ("Car Loan", AccountType.LOAN, -500000),
    ]

    accounts = []
    for name, account_type, _ in accounts_data:
        acc = Account(
            budget_id=budget.id,
            name=name,
            account_type=account_type,
        )
        accounts.append(acc)
    session.add_all(accounts)
    await session.flush()

    # Create transactions for each account
    transactions = []
    for acc, (_, _, amount) in zip(accounts, accounts_data, strict=True):
        txn = create_balance_transaction(budget.id, acc.id, amount, start_of_month)
        transactions.append(txn)
    session.add_all(transactions)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Assets: 1000 + 2000 + 3000 + 500 + 5000 + 250 = $11,750 (1175000 cents)
    assert data["current_total_assets"] == 1175000

    # Liabilities: 1000 + 5000 = $6,000 (600000 cents)
    assert data["current_total_liabilities"] == 600000

    # Net worth: 11750 - 6000 = $5,750
    assert data["current_net_worth"] == 575000

    # Check classification in account items
    period = data["periods"][0]
    for acc in period["accounts"]:
        if acc["account_type"] in ["credit_card", "loan"]:
            assert acc["is_liability"] is True
        else:
            assert acc["is_liability"] is False


async def test_net_worth_excludes_scheduled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scheduled (future) transactions don't affect balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(checking)
    await session.flush()

    # Create opening balance transaction
    opening_txn = create_balance_transaction(
        budget.id, checking.id, 500000, start_of_month
    )
    # Add a scheduled transaction (should NOT affect balance calculation)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=today + timedelta(days=30),
        amount=-100000,  # -$1,000
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([opening_txn, scheduled_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Balance should be unchanged by scheduled transaction
    assert data["current_total_assets"] == 500000


async def test_net_worth_multiple_months(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test net worth calculation across multiple months."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(checking)
    await session.flush()

    # Create transactions in different months
    dec = date(2023, 12, 15)
    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    # Opening balance in December = $5,000 (before the report period)
    opening_txn = create_balance_transaction(budget.id, checking.id, 500000, dec)
    # January deposit = +$2,000 (total: $7,000)
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=jan,
        amount=200000,  # +$2,000
        is_cleared=True,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # February deposit = +$3,000 (total: $10,000)
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=feb,
        amount=300000,  # +$3,000
        is_cleared=True,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([opening_txn, txn1, txn2])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-02-29",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Should have 2 periods
    assert len(data["periods"]) == 2

    # January end balance: opening + jan deposit = $5,000 + $2,000 = $7,000
    assert data["periods"][0]["period_start"] == "2024-01-01"
    assert data["periods"][0]["total_assets"] == 700000

    # February end balance: $7,000 + $3,000 = $10,000
    assert data["periods"][1]["period_start"] == "2024-02-01"
    assert data["periods"][1]["total_assets"] == 1000000

    # Net worth change should be Feb - Jan = 10000 - 7000 = $3,000
    assert data["net_worth_change"] == 300000


async def test_net_worth_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no accounts."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["current_net_worth"] == 0
    assert data["current_total_assets"] == 0
    assert data["current_total_liabilities"] == 0
    assert data["periods"] == []


async def test_net_worth_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' net worth."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 403


async def test_net_worth_all_time(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test net worth with no start_date (all time) - should use earliest transaction."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(checking)
    await session.flush()

    # Create transactions going back several months
    today = date.today()
    six_months_ago = (
        date(today.year, today.month - 6, 1)
        if today.month > 6
        else date(today.year - 1, today.month + 6, 1)
    )

    # Opening balance 6 months ago = $4,000
    opening_txn = create_balance_transaction(
        budget.id, checking.id, 400000, six_months_ago
    )
    # Additional deposit = +$1,000 (total $5,000)
    txn = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=six_months_ago + timedelta(days=15),
        amount=100000,  # +$1,000
        is_cleared=True,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    session.add_all([opening_txn, txn])
    await session.flush()

    # Call without start_date (all time)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "end_date": str(today),
            # No start_date - should use earliest transaction date
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Should have multiple periods going back to the earliest transaction
    assert len(data["periods"]) >= 6  # At least 6 months

    # The start_date in response should be the first of the month of earliest transaction
    assert data["start_date"] == str(six_months_ago.replace(day=1))

    # Current net worth should be $5,000
    assert data["current_net_worth"] == 500000


async def test_net_worth_no_transactions_shows_zero(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that accounts with no transactions show zero balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    today = date.today()
    start_of_month = today.replace(day=1)

    # Create account with no transactions
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
    )
    session.add(checking)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/net-worth",
        params={
            "start_date": str(start_of_month),
            "end_date": str(today),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Account should show zero balance since there are no transactions
    assert data["current_total_assets"] == 0
    assert data["current_net_worth"] == 0
    assert len(data["periods"]) == 1
    assert data["periods"][0]["total_assets"] == 0
