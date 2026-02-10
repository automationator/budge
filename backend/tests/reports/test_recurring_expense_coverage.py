from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.users.models import User


async def test_recurring_expense_coverage_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic recurring expense coverage report."""
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
    payee = Payee(budget_id=budget.id, name="Netflix")
    envelope = Envelope(
        budget_id=budget.id,
        name="Subscriptions",
        current_balance=5000,  # $50
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create a recurring expense that's fully funded
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-1500,  # $15
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=15),
    )
    session.add(recurring)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_recurring"] == 1
    assert data["fully_funded_count"] == 1
    assert data["partially_funded_count"] == 0
    assert data["not_linked_count"] == 0
    assert data["total_shortfall"] == 0

    item = data["items"][0]
    assert item["payee_name"] == "Netflix"
    assert item["amount"] == -1500
    assert item["frequency"] == "Every 1 month"
    assert item["envelope_name"] == "Subscriptions"
    assert item["funding_status"] == "funded"
    assert item["shortfall"] == 0


async def test_recurring_expense_coverage_partially_funded(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test recurring expense that's partially funded."""
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
    payee = Payee(budget_id=budget.id, name="Electric Bill")
    envelope = Envelope(
        budget_id=budget.id,
        name="Utilities",
        current_balance=5000,  # $50
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    # Expense is $100, but only $50 in envelope
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-10000,  # $100
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=10),
    )
    session.add(recurring)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["fully_funded_count"] == 0
    assert data["partially_funded_count"] == 1
    assert data["total_shortfall"] == 5000  # Need $50 more

    item = data["items"][0]
    assert item["funding_status"] == "partially_funded"
    assert item["shortfall"] == 5000


async def test_recurring_expense_coverage_not_linked(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test recurring expense with no linked envelope."""
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
    payee = Payee(budget_id=budget.id, name="Gym")
    session.add_all([account, payee])
    await session.flush()

    # No envelope linked
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=None,  # Not linked
        amount=-5000,  # $50
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=5),
    )
    session.add(recurring)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["fully_funded_count"] == 0
    assert data["partially_funded_count"] == 0
    assert data["not_linked_count"] == 1
    assert data["total_shortfall"] == 5000

    item = data["items"][0]
    assert item["envelope_id"] is None
    assert item["envelope_name"] is None
    assert item["funding_status"] == "not_linked"
    assert item["shortfall"] == 5000


async def test_recurring_expense_coverage_mixed_statuses(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test mix of funded, partially funded, and not linked."""
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
    payee1 = Payee(budget_id=budget.id, name="Netflix")
    payee2 = Payee(budget_id=budget.id, name="Electric")
    payee3 = Payee(budget_id=budget.id, name="Gym")
    funded_envelope = Envelope(
        budget_id=budget.id,
        name="Subscriptions",
        current_balance=5000,
    )
    partial_envelope = Envelope(
        budget_id=budget.id,
        name="Utilities",
        current_balance=5000,
    )
    session.add_all(
        [account, payee1, payee2, payee3, funded_envelope, partial_envelope]
    )
    await session.flush()

    # Fully funded: $15 expense, $50 balance
    r1 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee1.id,
        envelope_id=funded_envelope.id,
        amount=-1500,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=15),
    )
    # Partially funded: $100 expense, $50 balance
    r2 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee2.id,
        envelope_id=partial_envelope.id,
        amount=-10000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=10),
    )
    # Not linked: $50 expense
    r3 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee3.id,
        envelope_id=None,
        amount=-5000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=5),
    )
    session.add_all([r1, r2, r3])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_recurring"] == 3
    assert data["fully_funded_count"] == 1
    assert data["partially_funded_count"] == 1
    assert data["not_linked_count"] == 1
    # Shortfall: $50 (partial) + $50 (not linked) = $100
    assert data["total_shortfall"] == 10000


async def test_recurring_expense_coverage_frequency_formats(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test various frequency formats."""
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
    payee = Payee(budget_id=budget.id, name="Test")
    envelope = Envelope(
        budget_id=budget.id,
        name="Test",
        current_balance=100000,  # Plenty of balance
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create recurring with different frequencies
    r1 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-100,
        frequency_value=1,
        frequency_unit=FrequencyUnit.DAYS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=1),
    )
    r2 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-100,
        frequency_value=2,
        frequency_unit=FrequencyUnit.WEEKS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=14),
    )
    r3 = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-100,
        frequency_value=1,
        frequency_unit=FrequencyUnit.YEARS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=365),
    )
    session.add_all([r1, r2, r3])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    frequencies = [item["frequency"] for item in data["items"]]
    assert "Every 1 day" in frequencies
    assert "Every 2 weeks" in frequencies
    assert "Every 1 year" in frequencies


async def test_recurring_expense_coverage_excludes_income(
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

    # Recurring income (positive amount)
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=None,
        amount=500000,  # $5000 paycheck
        frequency_value=2,
        frequency_unit=FrequencyUnit.WEEKS,
        start_date=date.today(),
        next_occurrence_date=date.today() + timedelta(days=7),
    )
    session.add(recurring)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    # Income should be excluded
    assert data["total_recurring"] == 0
    assert data["items"] == []


async def test_recurring_expense_coverage_excludes_inactive(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that inactive recurring transactions are excluded."""
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
    payee = Payee(budget_id=budget.id, name="Old Subscription")
    session.add_all([account, payee])
    await session.flush()

    # Inactive recurring expense
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=None,
        amount=-1000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today() - timedelta(days=60),
        next_occurrence_date=date.today() + timedelta(days=5),
        is_active=False,  # Inactive
    )
    session.add(recurring)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    # Inactive should be excluded
    assert data["total_recurring"] == 0


async def test_recurring_expense_coverage_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no recurring expenses."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_recurring"] == 0
    assert data["fully_funded_count"] == 0
    assert data["partially_funded_count"] == 0
    assert data["not_linked_count"] == 0
    assert data["total_shortfall"] == 0
    assert data["items"] == []


async def test_recurring_expense_coverage_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/recurring-expense-coverage"
    )
    assert response.status_code == 403
