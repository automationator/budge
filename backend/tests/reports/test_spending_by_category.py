from datetime import date, timedelta

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


async def test_spending_by_category_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic spending aggregation by envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    dining = Envelope(budget_id=budget.id, name="Dining", current_balance=0)
    session.add_all([account, payee, groceries, dining])
    await session.flush()

    today = date.today()

    # Create transactions with allocations
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-2000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn1, txn2, txn3])
    await session.flush()

    # Create allocations
    from uuid import uuid7

    group1 = uuid7()
    group2 = uuid7()
    group3 = uuid7()

    alloc1 = Allocation(
        budget_id=budget.id,
        envelope_id=groceries.id,
        transaction_id=txn1.id,
        group_id=group1,
        amount=-5000,
        date=txn1.date,
    )
    alloc2 = Allocation(
        budget_id=budget.id,
        envelope_id=groceries.id,
        transaction_id=txn2.id,
        group_id=group2,
        amount=-3000,
        date=txn2.date,
    )
    alloc3 = Allocation(
        budget_id=budget.id,
        envelope_id=dining.id,
        transaction_id=txn3.id,
        group_id=group3,
        amount=-2000,
        date=txn3.date,
    )
    session.add_all([alloc1, alloc2, alloc3])
    await session.flush()

    # Call the report endpoint
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] is None
    assert data["end_date"] is None
    assert len(data["items"]) == 2

    # Sort by name for consistent testing
    items = sorted(data["items"], key=lambda x: x["envelope_name"])

    # Dining: 1 transaction, -2000 spent
    assert items[0]["envelope_name"] == "Dining"
    assert items[0]["total_spent"] == -2000
    assert items[0]["total_received"] == 0
    assert items[0]["net"] == -2000
    assert items[0]["transaction_count"] == 1

    # Groceries: 2 transactions, -8000 spent
    assert items[1]["envelope_name"] == "Groceries"
    assert items[1]["total_spent"] == -8000
    assert items[1]["total_received"] == 0
    assert items[1]["net"] == -8000
    assert items[1]["transaction_count"] == 2


async def test_spending_by_category_with_date_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test spending report with date range filter."""
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
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    # Create transactions on different dates
    txn_today = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-1000,
        status=TransactionStatus.POSTED,
    )
    txn_yesterday = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=yesterday,
        amount=-2000,
        status=TransactionStatus.POSTED,
    )
    txn_last_week = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=last_week,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn_today, txn_yesterday, txn_last_week])
    await session.flush()

    from uuid import uuid7

    for txn in [txn_today, txn_yesterday, txn_last_week]:
        alloc = Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn.id,
            group_id=uuid7(),
            amount=txn.amount,
            date=txn.date,
        )
        session.add(alloc)
    await session.flush()

    # Filter to just today
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category",
        params={"start_date": str(today), "end_date": str(today)},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == str(today)
    assert data["end_date"] == str(today)
    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == -1000
    assert data["items"][0]["transaction_count"] == 1


async def test_spending_by_category_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test spending report with no matching transactions."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_spending_by_category_excludes_scheduled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scheduled (not posted) transactions are excluded."""
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

    # Create a scheduled transaction (should be excluded)
    future = date.today() + timedelta(days=30)
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=future,
        amount=-5000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(txn)
    await session.flush()

    from uuid import uuid7

    alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn.id,
        group_id=uuid7(),
        amount=-5000,
        date=txn.date,
    )
    session.add(alloc)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    # Scheduled transaction should not appear
    assert data["items"] == []


async def test_spending_by_category_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' reports."""
    # Get test_user2's budget (not test_user's)
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 403


async def test_spending_by_category_excludes_adjustment_transactions(
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
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add_all([account, envelope])
    await session.flush()

    today = date.today()

    # Create a normal STANDARD transaction (should be included)
    standard_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Create an ADJUSTMENT transaction (should be excluded - e.g., initial balance)
    adjustment_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=today,
        amount=-100000,  # Large amount to make it obvious if included
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
        memo="Starting balance",
    )
    session.add_all([standard_txn, adjustment_txn])
    await session.flush()

    from uuid import uuid7

    # Allocations for both transactions
    standard_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=standard_txn.id,
        group_id=uuid7(),
        amount=-5000,
        date=standard_txn.date,
    )
    adjustment_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=adjustment_txn.id,
        group_id=uuid7(),
        amount=-100000,
        date=adjustment_txn.date,
    )
    session.add_all([standard_alloc, adjustment_alloc])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the standard transaction should be counted, not the adjustment
    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == -5000  # Not -105000
    assert data["items"][0]["transaction_count"] == 1  # Not 2


async def test_spending_by_category_includes_averages(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that response includes average spending calculations based on date range."""
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

    # Create transactions totaling $100 spent
    today = date.today()
    start_date = today - timedelta(days=9)  # 10 day period (inclusive)

    from uuid import uuid7

    # Transaction 1: $60 at start of period
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=start_date,
        amount=-6000,  # -$60
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn1.id,
            group_id=uuid7(),
            amount=-6000,
            date=txn1.date,
        )
    )

    # Transaction 2: $40 at end of period
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-4000,  # -$40
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn2.id,
            group_id=uuid7(),
            amount=-4000,
            date=txn2.date,
        )
    )
    await session.flush()

    # Call with explicit date range (10 days)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category",
        params={"start_date": str(start_date), "end_date": str(today)},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify days_in_period is calculated correctly
    assert data["days_in_period"] == 10

    # Verify averages: $100 total / 10 days = $10/day
    item = data["items"][0]
    assert item["total_spent"] == -10000  # -$100
    assert item["average_daily"] == 1000  # $10/day
    assert item["average_weekly"] == 7000  # $70/week
    assert item["average_monthly"] == 30000  # $300/month
    assert item["average_yearly"] == 365000  # $3650/year


async def test_spending_by_category_averages_without_date_range(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that averages default to 30-day calculation when no date range specified."""
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

    from uuid import uuid7

    # Create a transaction
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=-3000,  # -$30
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
            amount=-3000,
            date=txn.date,
        )
    )
    await session.flush()

    # Call without date range
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    # Default to 30 days when no date range specified
    assert data["days_in_period"] == 30

    # Verify averages: $30 total / 30 days = $1/day
    item = data["items"][0]
    assert item["average_daily"] == 100  # $1/day
    assert item["average_weekly"] == 700  # $7/week
    assert item["average_monthly"] == 3000  # $30/month
    assert item["average_yearly"] == 36500  # $365/year


async def test_spending_by_category_excludes_linked_cc_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that linked credit card envelopes are excluded from spending report.

    Linked CC envelopes are auto-tracking envelopes for credit card balances.
    They should not appear in spending reports because the actual spending
    is already tracked in regular envelopes.
    """
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create accounts
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    credit_card = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=True,
    )
    session.add_all([checking, credit_card])
    await session.flush()

    # Create envelopes - one regular, one linked to credit card
    regular_envelope = Envelope(
        budget_id=budget.id, name="Groceries", current_balance=0
    )
    linked_cc_envelope = Envelope(
        budget_id=budget.id,
        name="Credit Card Payment",
        current_balance=0,
        linked_account_id=credit_card.id,
    )
    session.add_all([regular_envelope, linked_cc_envelope])
    await session.flush()

    payee = Payee(budget_id=budget.id, name="Store")
    session.add(payee)
    await session.flush()

    today = date.today()
    from uuid import uuid7

    # Transaction with allocation to regular envelope (should be included)
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        payee_id=payee.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=regular_envelope.id,
            transaction_id=txn1.id,
            group_id=uuid7(),
            amount=-5000,
            date=txn1.date,
        )
    )

    # Transaction with allocation to linked CC envelope (should be excluded)
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=credit_card.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=linked_cc_envelope.id,
            transaction_id=txn2.id,
            group_id=uuid7(),
            amount=-3000,
            date=txn2.date,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the regular envelope should appear, not the linked CC envelope
    assert len(data["items"]) == 1
    assert data["items"][0]["envelope_name"] == "Groceries"
    assert data["items"][0]["total_spent"] == -5000


async def test_spending_by_category_transaction_count_excludes_refunds(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transaction count only includes transactions with actual spending.

    Refunds (positive allocations) should not count toward transaction_count
    since they don't represent spending activity.
    """
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
    from uuid import uuid7

    # Transaction 1: Spending (-$50)
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-5000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn1.id,
            group_id=uuid7(),
            amount=-5000,
            date=txn1.date,
        )
    )

    # Transaction 2: Refund (+$20) - should NOT count toward transaction_count
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=2000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn2.id,
            group_id=uuid7(),
            amount=2000,
            date=txn2.date,
        )
    )

    # Transaction 3: Another spending (-$30)
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=-3000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn3)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn3.id,
            group_id=uuid7(),
            amount=-3000,
            date=txn3.date,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/spending-by-category"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    item = data["items"][0]

    # Transaction count should be 2 (only spending transactions), not 3
    assert item["transaction_count"] == 2

    # Total spent should be -8000 (only negative amounts)
    assert item["total_spent"] == -8000

    # Total received should be 2000 (positive allocation)
    assert item["total_received"] == 2000

    # Net should be -6000 (all allocations summed)
    assert item["net"] == -6000
