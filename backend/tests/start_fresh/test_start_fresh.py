from datetime import date
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocations.models import Allocation
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.locations.models import Location
from src.payees.models import Payee
from src.transactions.models import Transaction
from src.users.models import User
from tests.utils import TEST_USER_PASSWORD


async def test_preview_all_data(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test preview returns correct counts for ALL deletion."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope_group = EnvelopeGroup(budget_id=budget.id, name="Test Group")
    envelope = Envelope(budget_id=budget.id, name="Test Envelope")
    payee = Payee(budget_id=budget.id, name="Test Payee")
    location = Location(budget_id=budget.id, name="Test Location")
    session.add_all([account, envelope_group, envelope, payee, location])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
        payee_id=payee.id,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        transaction_id=transaction.id,
        envelope_id=envelope.id,
        amount=-1000,
        group_id=uuid4(),
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/start-fresh/preview",
        params={"categories": "all"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accounts_count"] >= 1
    assert data["transactions_count"] >= 1
    assert data["allocations_count"] >= 1
    assert data["envelopes_count"] >= 1
    assert data["envelope_groups_count"] >= 1
    assert data["payees_count"] >= 1
    assert data["locations_count"] >= 1


async def test_preview_selective_categories(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test preview returns correct counts for selective deletion."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope")
    session.add_all([account, envelope])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
    )
    session.add(transaction)
    await session.flush()

    # Preview only transactions
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/start-fresh/preview",
        params={"categories": "transactions"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["transactions_count"] >= 1
    assert data["accounts_count"] == 0  # Not selected
    assert data["envelopes_count"] == 0  # Not selected


async def test_start_fresh_requires_password(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test deletion requires correct password."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": "wrongpassword",
            "categories": ["all"],
        },
    )
    assert response.status_code == 401
    assert "password" in response.json()["detail"].lower()


async def test_start_fresh_deletes_all_data(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test ALL deletion clears everything."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope")
    payee = Payee(budget_id=budget.id, name="Test Payee")
    location = Location(budget_id=budget.id, name="Test Location")
    session.add_all([account, envelope, payee, location])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
        payee_id=payee.id,
    )
    session.add(transaction)
    await session.flush()

    # Delete all
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["all"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted"]["accounts_count"] >= 1
    assert data["deleted"]["transactions_count"] >= 1

    # Verify data is gone
    count_result = await session.execute(
        select(func.count()).select_from(Account).where(Account.budget_id == budget.id)
    )
    assert count_result.scalar() == 0


async def test_start_fresh_selective_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test selective deletion of transactions only."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope")
    session.add_all([account, envelope])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        transaction_id=transaction.id,
        envelope_id=envelope.id,
        amount=-1000,
        group_id=uuid4(),
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    account_id = account.id
    envelope_id = envelope.id

    # Delete only transactions
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["transactions"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"]["transactions_count"] >= 1
    assert data["deleted"]["allocations_count"] >= 1

    # Account should still exist
    account_result = await session.execute(
        select(Account).where(Account.id == account_id)
    )
    assert account_result.scalar_one_or_none() is not None

    # Envelope should still exist
    envelope_result = await session.execute(
        select(Envelope).where(Envelope.id == envelope_id)
    )
    assert envelope_result.scalar_one_or_none() is not None


async def test_start_fresh_payees_only_deletes_unlinked(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that payee deletion only removes unlinked payees."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    linked_payee = Payee(budget_id=budget.id, name="Linked Payee")
    unlinked_payee = Payee(budget_id=budget.id, name="Unlinked Payee")
    session.add_all([account, linked_payee, unlinked_payee])
    await session.flush()

    # Create transaction linking to one payee
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
        payee_id=linked_payee.id,
    )
    session.add(transaction)
    await session.flush()

    linked_payee_id = linked_payee.id
    unlinked_payee_id = unlinked_payee.id

    # Delete only payees (without transactions)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["payees"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"]["payees_count"] == 1  # Only unlinked

    # Linked payee should still exist
    linked_result = await session.execute(
        select(Payee).where(Payee.id == linked_payee_id)
    )
    assert linked_result.scalar_one_or_none() is not None

    # Unlinked payee should be gone
    unlinked_result = await session.execute(
        select(Payee).where(Payee.id == unlinked_payee_id)
    )
    assert unlinked_result.scalar_one_or_none() is None


async def test_start_fresh_non_owner_forbidden(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that non-owners cannot use start fresh."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a member (not owner)
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": "password",
            "categories": ["all"],
        },
    )
    assert response.status_code == 403


async def test_start_fresh_admin_forbidden(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Test that even admins cannot use start fresh (owner only)."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as admin
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": "password",
            "categories": ["all"],
        },
    )
    assert response.status_code == 403


async def test_start_fresh_unauthorized(client: AsyncClient) -> None:
    """Test unauthenticated request is rejected."""
    response = await client.post(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/start-fresh",
        json={
            "password": "password",
            "categories": ["all"],
        },
    )
    assert response.status_code == 401


async def test_preview_accounts_includes_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that previewing accounts category includes transaction counts."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    session.add(account)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-1000,
    )
    session.add(transaction)
    await session.flush()

    # Preview accounts (should cascade to transactions)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/start-fresh/preview",
        params={"categories": "accounts"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accounts_count"] >= 1
    assert data["transactions_count"] >= 1  # Cascaded


async def test_preview_allocations_category(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test preview returns correct counts for allocations category."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data with allocations
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope", current_balance=5000)
    session.add_all([account, envelope])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-5000,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        transaction_id=transaction.id,
        envelope_id=envelope.id,
        amount=-5000,
        group_id=uuid4(),
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/start-fresh/preview",
        params={"categories": "allocations"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allocations_count"] >= 1
    assert data["envelopes_cleared_count"] >= 1
    # Should not include transactions or envelopes for deletion
    assert data["transactions_count"] == 0
    assert data["envelopes_count"] == 0


async def test_start_fresh_clears_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test clearing allocations deletes records and resets envelope balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope", current_balance=5000)
    session.add_all([account, envelope])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-5000,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        transaction_id=transaction.id,
        envelope_id=envelope.id,
        amount=-5000,
        group_id=uuid4(),
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    envelope_id = envelope.id
    transaction_id = transaction.id

    # Clear allocations
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["allocations"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted"]["allocations_count"] >= 1
    assert data["deleted"]["envelopes_cleared_count"] >= 1

    # Verify allocations are deleted
    alloc_result = await session.execute(
        select(func.count())
        .select_from(Allocation)
        .where(Allocation.budget_id == budget.id)
    )
    assert alloc_result.scalar() == 0

    # Verify envelope balance is reset but envelope still exists
    envelope_result = await session.execute(
        select(Envelope).where(Envelope.id == envelope_id)
    )
    envelope_obj = envelope_result.scalar_one()
    assert envelope_obj is not None
    assert envelope_obj.current_balance == 0

    # Verify transaction still exists
    txn_result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    assert txn_result.scalar_one_or_none() is not None


async def test_clear_allocations_preserves_unallocated_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that unallocated envelope is not modified when clearing allocations."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create unallocated envelope (normally created by system)
    unallocated = Envelope(
        budget_id=budget.id,
        name="Unallocated",
        is_unallocated=True,
        current_balance=10000,  # This value is ignored in practice, calculated dynamically
    )
    regular_envelope = Envelope(
        budget_id=budget.id, name="Regular Envelope", current_balance=5000
    )
    session.add_all([unallocated, regular_envelope])
    await session.flush()

    unallocated_id = unallocated.id
    regular_id = regular_envelope.id

    # Clear allocations
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["allocations"],
        },
    )
    assert response.status_code == 200

    # Regular envelope balance should be reset
    reg_result = await session.execute(
        select(Envelope).where(Envelope.id == regular_id)
    )
    reg = reg_result.scalar_one()
    assert reg.current_balance == 0

    # Unallocated envelope should still exist and be unmodified
    # (its balance is calculated dynamically, but the is_unallocated flag should prevent direct modification)
    unalloc_result = await session.execute(
        select(Envelope).where(Envelope.id == unallocated_id)
    )
    unalloc = unalloc_result.scalar_one()
    assert unalloc is not None
    assert unalloc.is_unallocated is True
    # The balance should NOT be reset since it's the unallocated envelope
    assert unalloc.current_balance == 10000


async def test_start_fresh_transactions_resets_account_balances(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that deleting transactions resets account balances to 0."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account with non-zero balances
    account = Account(
        budget_id=budget.id,
        name="Test Account",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,  # $100.00 cleared
        uncleared_balance=5000,  # $50.00 uncleared
    )
    session.add(account)
    await session.flush()

    # Create a transaction (the balance was set manually for this test)
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-5000,
        is_cleared=True,
    )
    session.add(transaction)
    await session.flush()

    account_id = account.id

    # Delete only transactions
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["transactions"],
        },
    )
    assert response.status_code == 200
    assert response.json()["deleted"]["transactions_count"] >= 1

    # Account should still exist but balances should be 0
    account_result = await session.execute(
        select(Account).where(Account.id == account_id)
    )
    updated_account = account_result.scalar_one()
    assert updated_account is not None
    assert updated_account.cleared_balance == 0
    assert updated_account.uncleared_balance == 0


async def test_start_fresh_transactions_resets_envelope_balances(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that deleting transactions resets envelope balances to 0."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create test data
    account = Account(
        budget_id=budget.id, name="Test Account", account_type=AccountType.CHECKING
    )
    envelope = Envelope(budget_id=budget.id, name="Test Envelope", current_balance=5000)
    unallocated = Envelope(
        budget_id=budget.id,
        name="Unallocated",
        is_unallocated=True,
        current_balance=10000,
    )
    session.add_all([account, envelope, unallocated])
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date.today(),
        amount=-5000,
    )
    session.add(transaction)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        transaction_id=transaction.id,
        envelope_id=envelope.id,
        amount=-5000,
        group_id=uuid4(),
        date=transaction.date,
    )
    session.add(allocation)
    await session.flush()

    envelope_id = envelope.id
    unallocated_id = unallocated.id

    # Delete transactions (not "allocations" category specifically)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/start-fresh",
        json={
            "password": TEST_USER_PASSWORD,
            "categories": ["transactions"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"]["transactions_count"] >= 1
    assert data["deleted"]["allocations_count"] >= 1
    # Should report envelopes_cleared_count since envelope balances are reset
    assert data["deleted"]["envelopes_cleared_count"] >= 1

    # Regular envelope balance should be reset to 0
    envelope_result = await session.execute(
        select(Envelope).where(Envelope.id == envelope_id)
    )
    updated_envelope = envelope_result.scalar_one()
    assert updated_envelope.current_balance == 0

    # Unallocated envelope should NOT be reset (it's calculated dynamically)
    unalloc_result = await session.execute(
        select(Envelope).where(Envelope.id == unallocated_id)
    )
    unalloc = unalloc_result.scalar_one()
    assert unalloc.current_balance == 10000
