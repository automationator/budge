from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.transactions.models import Transaction, TransactionStatus
from src.users.models import User


async def test_upcoming_expenses_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic upcoming expenses retrieval."""
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
    payee = Payee(budget_id=budget.id, name="Insurance Co")
    envelope = Envelope(budget_id=budget.id, name="Insurance", current_balance=50000)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create recurring transaction linked to envelope
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        amount=-10000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=15),
        envelope_id=envelope.id,
    )
    session.add(recurring)
    await session.flush()

    # Create scheduled transaction
    future_date = date.today() + timedelta(days=15)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        recurring_transaction_id=recurring.id,
        date=future_date,
        amount=-10000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["as_of_date"] == str(date.today())
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["amount"] == -10000
    assert item["payee_name"] == "Insurance Co"
    assert item["envelope_name"] == "Insurance"
    assert item["envelope_balance"] == 50000
    assert item["days_away"] == 15
    assert item["funding_status"] == "funded"


async def test_upcoming_expenses_needs_attention(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test expense marked as needs_attention when envelope underfunded."""
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
    payee = Payee(budget_id=budget.id, name="Rent")
    # Envelope has less than expense amount
    envelope = Envelope(budget_id=budget.id, name="Housing", current_balance=50000)
    session.add_all([account, payee, envelope])
    await session.flush()

    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        amount=-100000,  # -$1000, more than envelope balance
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=5),
        envelope_id=envelope.id,
    )
    session.add(recurring)
    await session.flush()

    future_date = date.today() + timedelta(days=5)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        recurring_transaction_id=recurring.id,
        date=future_date,
        amount=-100000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["funding_status"] == "needs_attention"
    assert data["items"][0]["envelope_balance"] == 50000


async def test_upcoming_expenses_not_linked(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test expense marked as not_linked when no envelope associated."""
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
    payee = Payee(budget_id=budget.id, name="Misc Vendor")
    session.add_all([account, payee])
    await session.flush()

    # Recurring transaction without envelope
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        amount=-5000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=10),
        envelope_id=None,
    )
    session.add(recurring)
    await session.flush()

    future_date = date.today() + timedelta(days=10)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        recurring_transaction_id=recurring.id,
        date=future_date,
        amount=-5000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["funding_status"] == "not_linked"
    assert data["items"][0]["envelope_id"] is None
    assert data["items"][0]["envelope_name"] is None


async def test_upcoming_expenses_excludes_posted(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that posted transactions are not included."""
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

    # Posted transaction (should be excluded)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_upcoming_expenses_excludes_income(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that positive amounts (income) are excluded."""
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
    session.add_all([account, payee])
    await session.flush()

    # Scheduled income (should be excluded)
    future_date = date.today() + timedelta(days=14)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=future_date,
        amount=500000,  # Positive = income
        status=TransactionStatus.SCHEDULED,
    )
    session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_upcoming_expenses_days_ahead_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test the days_ahead parameter filters correctly."""
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
    payee = Payee(budget_id=budget.id, name="Utility")
    session.add_all([account, payee])
    await session.flush()

    # Transaction within 30 days
    txn_soon = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today() + timedelta(days=20),
        amount=-5000,
        status=TransactionStatus.SCHEDULED,
    )
    # Transaction beyond 30 days
    txn_later = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today() + timedelta(days=60),
        amount=-5000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add_all([txn_soon, txn_later])
    await session.flush()

    # Default is 90 days, should include both
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2

    # Filter to 30 days, should only include one
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses",
        params={"days_ahead": 30},
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


async def test_upcoming_expenses_sorted_by_date(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that results are sorted by date ascending."""
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
    payee = Payee(budget_id=budget.id, name="Vendor")
    session.add_all([account, payee])
    await session.flush()

    # Create in reverse order
    dates = [30, 10, 20, 5]
    for days in dates:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=date.today() + timedelta(days=days),
            amount=-1000,
            status=TransactionStatus.SCHEDULED,
        )
        session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 4
    # Should be sorted ascending by date
    days_away_values = [item["days_away"] for item in data["items"]]
    assert days_away_values == [5, 10, 20, 30]


async def test_upcoming_expenses_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/upcoming-expenses"
    )
    assert response.status_code == 403
