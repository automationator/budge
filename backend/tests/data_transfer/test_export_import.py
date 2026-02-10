"""Tests for data export/import functionality."""

from datetime import date
from uuid import uuid7

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocation_rules.models import AllocationRule, AllocationRuleType
from src.allocations.models import Allocation
from src.auth.service import create_access_token
from src.budgets.models import (
    Budget,
    BudgetMembership,
    BudgetRole,
    DefaultIncomeAllocation,
)
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.locations.models import Location
from src.notifications.models import Notification, NotificationType
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User
from tests.utils import TEST_USER2_PASSWORD, TEST_USER_PASSWORD


async def test_export_empty_budget(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test exporting a budget with no data."""
    # Create a fresh budget for this test
    budget = Budget(name="Export Test Budget", owner_id=test_user.id)
    session.add(budget)
    await session.flush()  # Flush to get budget.id

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/export")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["version"] == "1.0"
    assert data["budget"]["name"] == "Export Test Budget"
    assert data["accounts"] == []
    assert data["envelopes"] == []
    assert data["transactions"] == []


async def test_export_with_data(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test exporting a budget with various data."""
    # Create budget
    budget = Budget(name="Full Export Budget", owner_id=test_user.id)
    session.add(budget)
    await session.flush()

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    # Create account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=100000,
    )
    session.add(account)

    # Create envelope group
    group = EnvelopeGroup(budget_id=budget.id, name="Bills")
    session.add(group)
    await session.flush()

    # Create envelope
    envelope = Envelope(
        budget_id=budget.id,
        envelope_group_id=group.id,
        name="Groceries",
        current_balance=50000,
    )
    session.add(envelope)

    # Create payee
    payee = Payee(budget_id=budget.id, name="Supermarket")
    session.add(payee)

    # Create location
    location = Location(budget_id=budget.id, name="Home")
    session.add(location)
    await session.flush()

    # Create allocation rule
    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.PERCENTAGE,
        amount=5000,  # 50%
    )
    session.add(rule)

    # Create recurring transaction
    recurring = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date(2024, 1, 1),
        amount=-10000,
        next_occurrence_date=date(2024, 2, 1),
    )
    session.add(recurring)
    await session.flush()

    # Create transaction with allocation
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        location_id=location.id,
        date=date(2024, 1, 15),
        amount=-5000,
        transaction_type=TransactionType.STANDARD,
        status=TransactionStatus.POSTED,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=transaction.id,
        group_id=uuid7(),
        amount=-5000,
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/export")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["budget"]["name"] == "Full Export Budget"
    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["name"] == "Checking"
    assert data["accounts"][0]["cleared_balance"] == 100000
    assert data["accounts"][0]["uncleared_balance"] == 0

    assert len(data["envelope_groups"]) == 1
    assert data["envelope_groups"][0]["name"] == "Bills"

    assert len(data["envelopes"]) == 1
    assert data["envelopes"][0]["name"] == "Groceries"

    assert len(data["payees"]) == 1
    assert data["payees"][0]["name"] == "Supermarket"

    assert len(data["locations"]) == 1
    assert data["locations"][0]["name"] == "Home"

    assert len(data["allocation_rules"]) == 1
    assert data["allocation_rules"][0]["amount"] == 5000

    assert len(data["recurring_transactions"]) == 1
    assert data["recurring_transactions"][0]["amount"] == -10000

    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["amount"] == -5000

    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == -5000


async def test_import_to_new_budget(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test importing exported data to a new budget."""
    # First, create a budget with data and export it
    source_budget = Budget(name="Source Budget", owner_id=test_user.id)
    session.add(source_budget)
    await session.flush()

    source_membership = BudgetMembership(
        budget_id=source_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(source_membership)
    await session.flush()

    # Add some data
    account = Account(
        budget_id=source_budget.id,
        name="Import Test Account",
        account_type=AccountType.SAVINGS,
        cleared_balance=200000,
    )
    session.add(account)
    envelope = Envelope(
        budget_id=source_budget.id, name="Import Test Envelope", current_balance=75000
    )
    session.add(envelope)
    payee = Payee(budget_id=source_budget.id, name="Import Test Payee")
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=source_budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 1, 20),
        amount=-10000,
        transaction_type=TransactionType.STANDARD,
        status=TransactionStatus.POSTED,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=source_budget.id,
        envelope_id=envelope.id,
        transaction_id=transaction.id,
        group_id=uuid7(),
        amount=-10000,
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    # Export
    export_response = await authenticated_client.get(
        f"/api/v1/budgets/{source_budget.id}/export"
    )
    assert export_response.status_code == 200
    export_data = export_response.json()["data"]

    # Create destination budget
    dest_budget = Budget(name="Destination Budget", owner_id=test_user.id)
    session.add(dest_budget)
    await session.flush()

    dest_membership = BudgetMembership(
        budget_id=dest_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(dest_membership)
    await session.flush()

    # Import
    import_response = await authenticated_client.post(
        f"/api/v1/budgets/{dest_budget.id}/import",
        json={
            "data": export_data,
            "clear_existing": False,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert import_response.status_code == 200
    result = import_response.json()

    assert result["success"] is True
    assert result["accounts_imported"] == 1
    assert result["envelopes_imported"] == 1
    assert result["payees_imported"] == 1
    assert result["transactions_imported"] == 1
    assert result["allocations_imported"] == 1
    assert result["errors"] == []

    # Verify data was imported
    accounts = await session.execute(
        select(Account).where(Account.budget_id == dest_budget.id)
    )
    imported_accounts = accounts.scalars().all()
    assert len(imported_accounts) == 1
    assert imported_accounts[0].name == "Import Test Account"
    assert imported_accounts[0].cleared_balance == 200000


async def test_import_with_clear_existing(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test importing with clear_existing=True deletes existing data."""
    # Create budget with existing data
    budget = Budget(name="Clear Test Budget", owner_id=test_user.id)
    session.add(budget)
    await session.flush()

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    # Add existing account
    existing_account = Account(
        budget_id=budget.id,
        name="Existing Account",
        account_type=AccountType.CHECKING,
    )
    session.add(existing_account)
    await session.flush()

    # Create import data with different account
    import_data = {
        "version": "1.0",
        "exported_at": "2024-01-01T00:00:00Z",
        "budget": {"name": "Source Budget"},
        "accounts": [
            {
                "id": str(uuid7()),
                "budget_id": str(
                    uuid7()
                ),  # Will be ignored, uses destination budget_id
                "name": "New Account",
                "account_type": "savings",
                "icon": None,
                "description": None,
                "sort_order": 0,
                "include_in_budget": True,
                "is_active": True,
                "cleared_balance": 50000,
                "uncleared_balance": 0,
                "last_reconciled_at": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": None,
            }
        ],
        "envelope_groups": [],
        "envelopes": [],
        "payees": [],
        "locations": [],
        "allocation_rules": [],
        "recurring_transactions": [],
        "transactions": [],
        "allocations": [],
    }

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/import",
        json={
            "data": import_data,
            "clear_existing": True,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["accounts_imported"] == 1

    # Verify only new account exists
    accounts = await session.execute(
        select(Account).where(Account.budget_id == budget.id)
    )
    imported_accounts = accounts.scalars().all()
    assert len(imported_accounts) == 1
    assert imported_accounts[0].name == "New Account"


async def test_export_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users can't export other budget's data."""
    # Create budget owned by test_user2
    budget = Budget(name="Other Budget", owner_id=test_user2.id)
    session.add(budget)
    await session.flush()

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user2.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    # test_user (authenticated) tries to export
    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/export")
    assert response.status_code == 403


async def test_import_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users can't import to other budget's."""
    # Create budget owned by test_user2
    budget = Budget(name="Other Budget Import", owner_id=test_user2.id)
    session.add(budget)
    await session.flush()

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user2.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    import_data = {
        "version": "1.0",
        "exported_at": "2024-01-01T00:00:00Z",
        "budget": {"name": "Source"},
        "accounts": [],
        "envelope_groups": [],
        "envelopes": [],
        "payees": [],
        "locations": [],
        "allocation_rules": [],
        "recurring_transactions": [],
        "transactions": [],
        "allocations": [],
    }

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/import",
        json={
            "data": import_data,
            "clear_existing": False,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert response.status_code == 403


async def test_export_preserves_relationships(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that export preserves entity relationships via IDs."""
    budget = Budget(name="Relationship Test", owner_id=test_user.id)
    session.add(budget)
    await session.flush()

    membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    # Create envelope group and envelope with relationship
    group = EnvelopeGroup(budget_id=budget.id, name="Test Group")
    session.add(group)
    await session.flush()

    envelope = Envelope(
        budget_id=budget.id, envelope_group_id=group.id, name="Child Envelope"
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/export")
    assert response.status_code == 200
    data = response.json()["data"]

    # Verify relationship is preserved
    assert len(data["envelope_groups"]) == 1
    assert len(data["envelopes"]) == 1
    assert data["envelopes"][0]["envelope_group_id"] == data["envelope_groups"][0]["id"]


async def test_import_remaps_relationships(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that import generates new IDs but maintains relationships."""
    # Create source budget
    source_budget = Budget(name="Remap Source", owner_id=test_user.id)
    session.add(source_budget)
    await session.flush()

    source_membership = BudgetMembership(
        budget_id=source_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(source_membership)
    await session.flush()

    # Create related entities
    group = EnvelopeGroup(budget_id=source_budget.id, name="Remap Group")
    session.add(group)
    await session.flush()

    envelope = Envelope(
        budget_id=source_budget.id, envelope_group_id=group.id, name="Remap Envelope"
    )
    session.add(envelope)
    await session.flush()

    # Export
    export_response = await authenticated_client.get(
        f"/api/v1/budgets/{source_budget.id}/export"
    )
    export_data = export_response.json()["data"]
    original_group_id = export_data["envelope_groups"][0]["id"]
    original_envelope_id = export_data["envelopes"][0]["id"]

    # Create destination budget
    dest_budget = Budget(name="Remap Dest", owner_id=test_user.id)
    session.add(dest_budget)
    await session.flush()

    dest_membership = BudgetMembership(
        budget_id=dest_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(dest_membership)
    await session.flush()

    # Import
    import_response = await authenticated_client.post(
        f"/api/v1/budgets/{dest_budget.id}/import",
        json={
            "data": export_data,
            "clear_existing": False,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert import_response.status_code == 200

    # Verify IDs changed but relationship maintained
    groups = await session.execute(
        select(EnvelopeGroup).where(EnvelopeGroup.budget_id == dest_budget.id)
    )
    new_group = groups.scalar_one()
    assert str(new_group.id) != original_group_id

    envelopes = await session.execute(
        select(Envelope).where(Envelope.budget_id == dest_budget.id)
    )
    new_envelope = envelopes.scalar_one()
    assert str(new_envelope.id) != original_envelope_id
    assert new_envelope.envelope_group_id == new_group.id


async def test_non_owner_cannot_import(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that viewers cannot import data."""
    budget = Budget(name="Viewer Import Test", owner_id=test_user.id)
    session.add(budget)
    await session.flush()

    owner_membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(owner_membership)
    viewer_membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user2.id, role=BudgetRole.ADMIN
    )
    session.add(viewer_membership)
    await session.flush()

    # Authenticate as viewer
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    import_data = {
        "version": "1.0",
        "exported_at": "2024-01-01T00:00:00Z",
        "budget": {"name": "Source"},
        "accounts": [],
        "envelope_groups": [],
        "envelopes": [],
        "payees": [],
        "locations": [],
        "allocation_rules": [],
        "recurring_transactions": [],
        "transactions": [],
        "allocations": [],
    }

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/import",
        json={
            "data": import_data,
            "clear_existing": False,
            "password": TEST_USER2_PASSWORD,
        },
    )
    assert response.status_code == 403


async def test_non_owner_cannot_export(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that viewers can export data (read-only operation)."""
    budget = Budget(name="Viewer Export Test", owner_id=test_user.id)
    session.add(budget)
    await session.flush()

    owner_membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
    )
    session.add(owner_membership)
    viewer_membership = BudgetMembership(
        budget_id=budget.id, user_id=test_user2.id, role=BudgetRole.ADMIN
    )
    session.add(viewer_membership)
    await session.flush()

    # Authenticate as viewer
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/export")
    assert response.status_code == 403


async def test_default_income_allocation_round_trip(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that default_income_allocation is preserved during export/import."""
    # Create source budget with non-default income allocation
    source_budget = Budget(
        name="Income Alloc Source",
        owner_id=test_user.id,
        default_income_allocation=DefaultIncomeAllocation.ENVELOPE,
    )
    session.add(source_budget)
    await session.flush()
    session.add(
        BudgetMembership(
            budget_id=source_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
        )
    )
    await session.flush()

    # Export
    export_response = await authenticated_client.get(
        f"/api/v1/budgets/{source_budget.id}/export"
    )
    assert export_response.status_code == 200
    export_data = export_response.json()["data"]
    assert export_data["budget"]["default_income_allocation"] == "envelope"

    # Create destination budget (starts with default RULES)
    dest_budget = Budget(name="Income Alloc Dest", owner_id=test_user.id)
    session.add(dest_budget)
    await session.flush()
    session.add(
        BudgetMembership(
            budget_id=dest_budget.id, user_id=test_user.id, role=BudgetRole.OWNER
        )
    )
    await session.flush()

    import_response = await authenticated_client.post(
        f"/api/v1/budgets/{dest_budget.id}/import",
        json={
            "data": export_data,
            "clear_existing": False,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert import_response.status_code == 200
    assert import_response.json()["success"] is True

    # Verify setting was applied
    await session.refresh(dest_budget)
    assert dest_budget.default_income_allocation == DefaultIncomeAllocation.ENVELOPE


async def test_import_without_default_income_allocation_backward_compat(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that importing old exports without default_income_allocation uses RULES default."""
    budget = Budget(
        name="Backward Compat Test",
        owner_id=test_user.id,
        default_income_allocation=DefaultIncomeAllocation.UNALLOCATED,
    )
    session.add(budget)
    await session.flush()
    session.add(
        BudgetMembership(
            budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
        )
    )
    await session.flush()

    # Import data without default_income_allocation field (old export format)
    import_data = {
        "version": "1.0",
        "exported_at": "2024-01-01T00:00:00Z",
        "budget": {"name": "Old Format Budget"},
        "accounts": [],
        "envelope_groups": [],
        "envelopes": [],
        "payees": [],
        "locations": [],
        "allocation_rules": [],
        "recurring_transactions": [],
        "transactions": [],
        "allocations": [],
    }

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/import",
        json={
            "data": import_data,
            "clear_existing": False,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Should default to RULES (the Pydantic default)
    await session.refresh(budget)
    assert budget.default_income_allocation == DefaultIncomeAllocation.RULES


async def test_notifications_cleared_on_replace_import(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that notifications are deleted when importing with clear_existing=True."""
    budget = Budget(name="Notification Clear Test", owner_id=test_user.id)
    session.add(budget)
    await session.flush()
    session.add(
        BudgetMembership(
            budget_id=budget.id, user_id=test_user.id, role=BudgetRole.OWNER
        )
    )
    await session.flush()

    # Create a notification
    notification = Notification(
        budget_id=budget.id,
        user_id=test_user.id,
        notification_type=NotificationType.LOW_BALANCE,
        title="Low balance",
        message="Your envelope balance is low",
    )
    session.add(notification)
    await session.flush()

    # Verify notification exists
    result = await session.execute(
        select(Notification).where(Notification.budget_id == budget.id)
    )
    assert len(result.scalars().all()) == 1

    # Import with clear_existing=True
    import_data = {
        "version": "1.0",
        "exported_at": "2024-01-01T00:00:00Z",
        "budget": {"name": "Fresh Import"},
        "accounts": [],
        "envelope_groups": [],
        "envelopes": [],
        "payees": [],
        "locations": [],
        "allocation_rules": [],
        "recurring_transactions": [],
        "transactions": [],
        "allocations": [],
    }

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/import",
        json={
            "data": import_data,
            "clear_existing": True,
            "password": TEST_USER_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify notifications were cleared
    result = await session.execute(
        select(Notification).where(Notification.budget_id == budget.id)
    )
    assert len(result.scalars().all()) == 0
