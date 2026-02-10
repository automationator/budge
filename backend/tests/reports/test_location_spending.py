from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.locations.models import Location
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User


async def test_location_spending_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic location spending report."""
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Create transactions at this location
    for amount in [-10000, -15000]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            location_id=location.id,
            date=today,
            amount=amount,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["include_no_location"] is True
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["location_name"] == "New York"
    assert item["total_spent"] == 25000  # $100 + $150
    assert item["transaction_count"] == 2
    assert item["average_amount"] == 12500


async def test_location_spending_multiple_locations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test multiple locations sorted by total spent."""
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
    ny = Location(budget_id=budget.id, name="New York")
    ohio = Location(budget_id=budget.id, name="Ohio")
    session.add_all([account, payee, ny, ohio])
    await session.flush()

    today = date.today()

    # NY: $500, Ohio: $200
    for location, amount in [(ny, -50000), (ohio, -20000)]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            location_id=location.id,
            date=today,
            amount=amount,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by total spent (descending)
    assert len(data["items"]) == 2
    assert data["items"][0]["location_name"] == "New York"
    assert data["items"][0]["total_spent"] == 50000
    assert data["items"][1]["location_name"] == "Ohio"
    assert data["items"][1]["total_spent"] == 20000


async def test_location_spending_includes_no_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transactions without location are included."""
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Transaction with location
    txn_with = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Transaction without location
    txn_without = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=None,
        date=today,
        amount=-20000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn_with, txn_without])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 2
    # Find no-location item
    no_loc_item = next(i for i in data["items"] if i["location_id"] is None)
    assert no_loc_item["location_name"] == "(No location)"
    assert no_loc_item["total_spent"] == 20000


async def test_location_spending_exclude_no_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test excluding transactions without location."""
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Transaction with location
    txn_with = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Transaction without location
    txn_without = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=None,
        date=today,
        amount=-20000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([txn_with, txn_without])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending",
        params={"include_no_location": False},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["include_no_location"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["location_name"] == "New York"


async def test_location_spending_date_filter(
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    for txn_date in [jan, feb]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            location_id=location.id,
            date=txn_date,
            amount=-10000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    # Filter to January only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-31"
    assert len(data["items"]) == 1
    assert data["items"][0]["transaction_count"] == 1


async def test_location_spending_filter_by_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering to specific locations."""
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
    ny = Location(budget_id=budget.id, name="New York")
    ohio = Location(budget_id=budget.id, name="Ohio")
    session.add_all([account, payee, ny, ohio])
    await session.flush()

    today = date.today()

    for location in [ny, ohio]:
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            location_id=location.id,
            date=today,
            amount=-10000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
    await session.flush()

    # Filter to NY only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending",
        params={"location_id": str(ny.id)},
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["location_name"] == "New York"


async def test_location_spending_excludes_income(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that positive transactions are excluded."""
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Expense
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Income (should be excluded)
    income_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=50000,
        status=TransactionStatus.POSTED,
    )
    session.add_all([expense_txn, income_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == 10000


async def test_location_spending_excludes_scheduled(
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Posted
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
    )
    # Scheduled (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today + timedelta(days=7),
        amount=-20000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add_all([posted_txn, scheduled_txn])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["total_spent"] == 10000


async def test_location_spending_empty(
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
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_location_spending_unauthorized(
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
        f"/api/v1/budgets/{other_budget.id}/reports/location-spending"
    )
    assert response.status_code == 403


async def test_location_spending_excludes_adjustments(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that adjustment transactions are excluded from location spending."""
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
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([account, payee, location])
    await session.flush()

    today = date.today()

    # Regular expense (should be included)
    regular_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )
    # Adjustment with location (should be excluded)
    adjustment_with_location = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-50000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
    )
    # Adjustment without location (should be excluded from no-location bucket)
    adjustment_no_location = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=None,
        date=today,
        amount=-100000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.ADJUSTMENT,
    )
    session.add_all([regular_txn, adjustment_with_location, adjustment_no_location])
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the regular transaction should be included
    assert len(data["items"]) == 1
    assert data["items"][0]["location_name"] == "New York"
    assert data["items"][0]["total_spent"] == 10000  # Only the $100 regular expense
    assert data["items"][0]["transaction_count"] == 1


async def test_location_spending_excludes_internal_transfers(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that internal transfers (budget → budget) are excluded."""
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
    credit_card = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    location = Location(budget_id=budget.id, name="New York")
    session.add_all([checking, credit_card, payee, location])
    await session.flush()

    today = date.today()

    # Regular expense (should be included)
    regular_txn = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        payee_id=payee.id,
        location_id=location.id,
        date=today,
        amount=-10000,
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.STANDARD,
    )

    # Internal transfer: checking → credit card (both budget accounts)
    # This should be EXCLUDED - it's just moving money within the budget
    transfer_out = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        payee_id=None,
        location_id=None,
        date=today,
        amount=-50000,  # Payment to credit card
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    transfer_in = Transaction(
        budget_id=budget.id,
        account_id=credit_card.id,
        payee_id=None,
        location_id=None,
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
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    # Only the regular expense should be included, not the internal transfer
    assert len(data["items"]) == 1
    assert data["items"][0]["location_name"] == "New York"
    assert data["items"][0]["total_spent"] == 10000


async def test_location_spending_includes_transfers_to_tracking(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transfers to tracking accounts ARE included (money leaving budget)."""
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
    payee = Payee(budget_id=budget.id, name="Store")
    session.add_all([checking, investment, payee])
    await session.flush()

    today = date.today()

    # Transfer: checking → investment (budget → tracking)
    # This SHOULD be included - money is leaving the budget
    transfer_out = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        payee_id=None,
        location_id=None,
        date=today,
        amount=-25000,  # $250 to investment
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.TRANSFER,
    )
    transfer_in = Transaction(
        budget_id=budget.id,
        account_id=investment.id,
        payee_id=None,
        location_id=None,
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
        f"/api/v1/budgets/{budget.id}/reports/location-spending"
    )
    assert response.status_code == 200
    data = response.json()

    # The transfer to tracking should appear in "(No location)"
    assert len(data["items"]) == 1
    assert data["items"][0]["location_id"] is None
    assert data["items"][0]["location_name"] == "(No location)"
    assert data["items"][0]["total_spent"] == 25000
