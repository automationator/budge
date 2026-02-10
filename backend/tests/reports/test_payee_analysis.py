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


async def test_payee_analysis_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic payee analysis report."""
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
    payee = Payee(budget_id=budget.id, name="Whole Foods")
    session.add_all([account, payee])
    await session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create multiple transactions at the same payee
    for txn_date, amount in [(yesterday, -5000), (today, -7500)]:
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

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["payee_name"] == "Whole Foods"
    assert item["total_spent"] == 12500  # $50 + $75
    assert item["transaction_count"] == 2
    assert item["average_amount"] == 6250  # $125 / 2
    assert item["last_transaction_date"] == str(today)


async def test_payee_analysis_multiple_payees_sorted(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test multiple payees sorted by total spent."""
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
    whole_foods = Payee(budget_id=budget.id, name="Whole Foods")
    amazon = Payee(budget_id=budget.id, name="Amazon")
    shell = Payee(budget_id=budget.id, name="Shell Gas")
    session.add_all([account, whole_foods, amazon, shell])
    await session.flush()

    today = date.today()

    # Amazon: $500, Whole Foods: $300, Shell: $100
    spending = [
        (amazon.id, -50000),
        (whole_foods.id, -30000),
        (shell.id, -10000),
    ]

    for payee_id, amount in spending:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee_id,
            date=today,
            amount=amount,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by total spent (descending)
    assert len(data["items"]) == 3
    assert data["items"][0]["payee_name"] == "Amazon"
    assert data["items"][0]["total_spent"] == 50000
    assert data["items"][1]["payee_name"] == "Whole Foods"
    assert data["items"][1]["total_spent"] == 30000
    assert data["items"][2]["payee_name"] == "Shell Gas"
    assert data["items"][2]["total_spent"] == 10000


async def test_payee_analysis_date_filter(
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

    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    for txn_date in [jan, feb]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=txn_date,
            amount=-10000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    # Filter to January only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-31"
    assert len(data["items"]) == 1
    assert data["items"][0]["transaction_count"] == 1
    assert data["items"][0]["last_transaction_date"] == "2024-01-15"


async def test_payee_analysis_envelope_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering by envelope."""
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

    today = date.today()

    # Transaction allocated to groceries
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=groceries.id,
            transaction_id=txn1.id,
            group_id=uuid7(),
            amount=-10000,
            date=today,
        )
    )

    # Transaction allocated to gas
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=gas.id,
            transaction_id=txn2.id,
            group_id=uuid7(),
            amount=-5000,
            date=today,
        )
    )
    await session.flush()

    # Filter to groceries only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis",
        params={"envelope_id": str(groceries.id)},
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == 10000
    assert data["items"][0]["transaction_count"] == 1


async def test_payee_analysis_min_total_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test minimum total spending filter."""
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
    big_spender = Payee(budget_id=budget.id, name="Big Store")
    small_spender = Payee(budget_id=budget.id, name="Small Store")
    session.add_all([account, big_spender, small_spender])
    await session.flush()

    today = date.today()

    # Big store: $500
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=big_spender.id,
        date=today,
        amount=-50000,
        status=TransactionStatus.POSTED,
    )
    # Small store: $50
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=small_spender.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn1, txn2])
    await session.flush()

    # Filter to min $100 total
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis",
        params={"min_total": 10000},  # $100 in cents
    )
    assert response.status_code == 200
    data = response.json()

    # Only big store should be included
    assert len(data["items"]) == 1
    assert data["items"][0]["payee_name"] == "Big Store"


async def test_payee_analysis_excludes_income(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that positive transactions (income) are excluded."""
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
    store = Payee(budget_id=budget.id, name="Store")
    employer = Payee(budget_id=budget.id, name="Employer")
    session.add_all([account, store, employer])
    await session.flush()

    today = date.today()

    # Expense
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=store.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Income (should be excluded)
    income_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=employer.id,
        date=today,
        amount=500000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([expense_txn, income_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 200
    data = response.json()

    # Only expense payee should be included
    assert len(data["items"]) == 1
    assert data["items"][0]["payee_name"] == "Store"


async def test_payee_analysis_excludes_scheduled(
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

    today = date.today()

    # Posted
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Scheduled (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today + timedelta(days=7),
        amount=-20000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add_all([posted_txn, scheduled_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 200
    data = response.json()

    # Only posted transaction should be counted
    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == 10000
    assert data["items"][0]["transaction_count"] == 1


async def test_payee_analysis_empty(
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
        f"/api/v1/budgets/{budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_payee_analysis_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/payee-analysis"
    )
    assert response.status_code == 403
