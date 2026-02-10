from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.envelopes.models import Envelope
from src.users.models import User


async def test_create_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={
            "name": "Groceries",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Groceries"
    assert data["current_balance"] == 0
    assert data["is_active"] is True
    assert data["is_unallocated"] is False
    assert data["target_balance"] is None


async def test_create_envelope_creates_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Creating the first envelope should also create the Unallocated envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # First, make sure there are no envelopes
    result = await session.execute(
        select(Envelope).where(Envelope.budget_id == budget.id)
    )
    existing = result.scalars().all()
    # Clean up any existing envelopes
    for env in existing:
        await session.delete(env)
    await session.flush()

    # Now create first envelope
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "First Envelope"},
    )
    assert response.status_code == 201

    # Check that Unallocated envelope was created
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = result.scalar_one_or_none()
    assert unallocated is not None
    assert unallocated.name == "Unallocated"
    assert unallocated.sort_order == -1  # Always first


async def test_create_envelope_with_all_fields(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={
            "name": "Emergency Fund",
            "icon": "🏦",
            "description": "For unexpected expenses",
            "sort_order": 5,
            "is_active": True,
            "target_balance": 100000,  # $1000.00 in cents
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Emergency Fund"
    assert data["icon"] == "🏦"
    assert data["description"] == "For unexpected expenses"
    assert data["sort_order"] == 5
    assert data["target_balance"] == 100000


async def test_create_duplicate_envelope_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create first envelope
    envelope = Envelope(
        budget_id=budget.id,
        name="Duplicate Test",
    )
    session.add(envelope)
    await session.flush()

    # Try to create envelope with same name
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Duplicate Test"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_cannot_create_envelope_named_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Users cannot create an envelope with the reserved name 'Unallocated'."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Unallocated"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_list_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some envelopes
    envelopes = [
        Envelope(budget_id=budget.id, name="Envelope B", sort_order=2),
        Envelope(budget_id=budget.id, name="Envelope A", sort_order=1),
        Envelope(budget_id=budget.id, name="Envelope C", sort_order=1),
    ]
    for env in envelopes:
        session.add(env)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/envelopes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    # Should be ordered by sort_order, then name
    names = [e["name"] for e in data if not e["is_unallocated"]][-3:]
    assert names == ["Envelope A", "Envelope C", "Envelope B"]


async def test_get_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Get Test Envelope",
        icon="💰",
        target_balance=50000,
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test Envelope"
    assert data["icon"] == "💰"
    assert data["target_balance"] == 50000


async def test_get_envelope_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/envelopes/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Update Test",
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}",
        json={
            "name": "Updated Name",
            "icon": "🎯",
            "target_balance": 25000,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["icon"] == "🎯"
    assert data["target_balance"] == 25000


async def test_update_envelope_duplicate_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope1 = Envelope(budget_id=budget.id, name="First Env")
    envelope2 = Envelope(budget_id=budget.id, name="Second Env")
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope2.id}",
        json={"name": "First Env"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_delete_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Delete Test")
    session.add(envelope)
    await session.flush()
    envelope_id = envelope.id

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await session.execute(select(Envelope).where(Envelope.id == envelope_id))
    assert result.scalar_one_or_none() is None


async def test_delete_envelope_increases_calculated_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting an envelope increases calculated unallocated (balance is dynamic)."""
    from src.accounts.models import Account, AccountType
    from src.envelopes.service import calculate_unallocated_balance

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account with balance (this creates the unallocated pool)
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=20000,
    )
    session.add(account)
    await session.flush()

    # Create envelope with balance
    envelope = Envelope(budget_id=budget.id, name="Has Money", current_balance=10000)
    session.add(envelope)
    await session.flush()

    # Calculate unallocated: account balance (20000) - envelope balance (10000) = 10000
    unallocated_before = await calculate_unallocated_balance(session, budget.id)
    assert unallocated_before == 10000

    # Delete the envelope
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}"
    )
    assert response.status_code == 204

    # Calculate unallocated: account balance (20000) - envelope balance (0) = 20000
    unallocated_after = await calculate_unallocated_balance(session, budget.id)
    assert (
        unallocated_after == 20000
    )  # Balance from deleted envelope now in unallocated


async def test_delete_envelope_with_negative_balance_decreases_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting an envelope with negative balance decreases calculated unallocated."""
    from src.accounts.models import Account, AccountType
    from src.envelopes.service import calculate_unallocated_balance

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account with balance
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    session.add(account)
    await session.flush()

    # Create envelope with negative balance (overspent)
    envelope = Envelope(budget_id=budget.id, name="Overspent", current_balance=-5000)
    session.add(envelope)
    await session.flush()

    # Calculate unallocated: account balance (50000) - envelope balance (-5000) = 55000
    unallocated_before = await calculate_unallocated_balance(session, budget.id)
    assert unallocated_before == 55000

    # Delete the envelope
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}"
    )
    assert response.status_code == 204

    # Calculate unallocated: account balance (50000) - envelope balance (0) = 50000
    unallocated_after = await calculate_unallocated_balance(session, budget.id)
    assert unallocated_after == 50000  # Negative balance no longer counted


async def test_delete_envelope_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_cannot_delete_unallocated_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope to trigger unallocated creation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Trigger Unallocated"},
    )
    assert response.status_code == 201

    # Find the unallocated envelope
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = result.scalar_one()

    # Try to delete it
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{unallocated.id}"
    )
    assert response.status_code == 400
    assert "cannot delete" in response.json()["detail"].lower()


async def test_cannot_rename_unallocated_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope to trigger unallocated creation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Trigger Unallocated 2"},
    )
    assert response.status_code == 201

    # Find the unallocated envelope
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = result.scalar_one()

    # Try to rename it
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/envelopes/{unallocated.id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 400
    assert "cannot rename" in response.json()["detail"].lower()


async def test_cannot_deactivate_unallocated_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope to trigger unallocated creation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Trigger Unallocated 3"},
    )
    assert response.status_code == 201

    # Find the unallocated envelope
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = result.scalar_one()

    # Try to deactivate it
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/envelopes/{unallocated.id}",
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert "cannot deactivate" in response.json()["detail"].lower()


async def test_can_update_unallocated_envelope_non_protected_fields(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """The unallocated envelope can have icon/description/target_balance updated."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an envelope to trigger unallocated creation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Trigger Unallocated 4"},
    )
    assert response.status_code == 201

    # Find the unallocated envelope
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = result.scalar_one()

    # Update non-protected fields
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/envelopes/{unallocated.id}",
        json={"icon": "📥", "description": "Incoming money"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["icon"] == "📥"
    assert data["description"] == "Incoming money"


# Authorization tests


async def test_envelope_unauthorized(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/envelopes"
    )
    assert response.status_code == 401


async def test_envelope_not_budget_member(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/envelopes")
    assert response.status_code == 403


async def test_member_can_read_envelopes(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/envelopes")
    assert response.status_code == 200


async def test_member_can_create_envelope(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Member Created Envelope"},
    )
    assert response.status_code == 201


async def test_member_cannot_delete_envelope(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Member Delete Test")
    session.add(envelope)

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}"
    )
    assert response.status_code == 403


async def test_viewer_can_only_read_envelopes(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.VIEWER,
    )
    session.add(membership)
    await session.flush()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Can read
    response = await client.get(f"/api/v1/budgets/{budget.id}/envelopes")
    assert response.status_code == 200

    # Cannot create
    response = await client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Viewer Envelope"},
    )
    assert response.status_code == 403


async def test_admin_can_delete_envelope(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Admin Delete Test")
    session.add(envelope)

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
    )
    session.add(membership)
    await session.flush()

    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{envelope.id}"
    )
    assert response.status_code == 204


# Credit Card Envelope Tests


async def test_cannot_delete_cc_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Credit card envelopes cannot be deleted directly - must delete the account."""

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account (which auto-creates the linked envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Test Credit Card",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201

    # Find the linked envelope
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.name == "Test Credit Card",
            Envelope.linked_account_id.isnot(None),
        )
    )
    cc_envelope = result.scalar_one()

    # Try to delete the CC envelope
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/envelopes/{cc_envelope.id}"
    )
    assert response.status_code == 400
    assert "credit card" in response.json()["detail"].lower()


async def test_cc_envelope_has_linked_account_id(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Credit card envelopes should have linked_account_id set in API response."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "API CC Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # List envelopes and find the CC envelope
    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/envelopes")
    assert response.status_code == 200
    envelopes = response.json()

    cc_envelope = next(
        (e for e in envelopes if e["name"] == "API CC Test"),
        None,
    )
    assert cc_envelope is not None
    assert cc_envelope["linked_account_id"] == account_id


async def test_cc_spending_does_not_affect_ready_to_assign(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Credit card spending should not affect Ready to Assign.

    Scenario:
    1. User has $100 in checking, allocates all to Groceries -> Ready to Assign = $0
    2. User adds CC account with $0 balance
    3. User spends $10 on CC from Groceries
    4. Expected: Ready to Assign stays at $0

    This verifies the formula: Non-CC Budget Accounts - All Envelopes (including CC)
    """
    from src.accounts.models import Account, AccountType
    from src.envelopes.service import calculate_unallocated_balance
    from src.payees.models import Payee

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Step 1: Create checking account with $100
    checking = Account(
        budget_id=budget.id,
        name="CC Test Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=10000,  # $100 in cents
    )
    session.add(checking)
    await session.flush()

    # Step 2: Create Groceries envelope and allocate all $100
    groceries = Envelope(
        budget_id=budget.id,
        name="CC Test Groceries",
        current_balance=10000,  # $100 allocated
    )
    session.add(groceries)
    await session.flush()

    # Verify Ready to Assign is $0
    ready_to_assign = await calculate_unallocated_balance(session, budget.id)
    assert ready_to_assign == 0, f"Expected $0 Ready to Assign, got {ready_to_assign}"

    # Step 3: Create CC account with $0 balance (auto-creates linked CC envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={"name": "CC Test Card", "account_type": "credit_card"},
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()

    # Verify Ready to Assign is still $0 after adding CC account
    ready_to_assign = await calculate_unallocated_balance(session, budget.id)
    assert ready_to_assign == 0, f"Expected $0 after adding CC, got {ready_to_assign}"

    # Step 4: Create a payee and spend $10 on CC from Groceries
    payee = Payee(budget_id=budget.id, name="CC Test Grocery Store")
    session.add(payee)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -1000,  # $10 expense
            "allocations": [{"envelope_id": str(groceries.id), "amount": -1000}],
        },
    )
    assert response.status_code == 201

    # Refresh envelopes
    await session.refresh(groceries)
    await session.refresh(cc_envelope)

    # Verify envelope moves happened correctly
    assert groceries.current_balance == 9000, (
        f"Expected Groceries $90, got {groceries.current_balance}"
    )
    assert cc_envelope.current_balance == 1000, (
        f"Expected CC envelope $10, got {cc_envelope.current_balance}"
    )

    # THE KEY ASSERTION: Ready to Assign should STILL be $0
    ready_to_assign = await calculate_unallocated_balance(session, budget.id)
    assert ready_to_assign == 0, (
        f"Expected Ready to Assign to stay at $0 after CC spending, got {ready_to_assign}"
    )


async def test_unfunded_cc_debt_calculation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that unfunded CC debt is calculated correctly.

    Unfunded CC debt = CC debt that exceeds CC envelope balance.
    """
    from uuid import UUID

    from src.accounts.models import Account
    from src.envelopes.service import calculate_unfunded_cc_debt

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account via API (starts with $0 balance)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Unfunded CC Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the account and set debt directly (simulating existing debt)
    result = await session.execute(
        select(Account).where(Account.id == UUID(cc_account_id))
    )
    cc_account = result.scalar_one()
    cc_account.cleared_balance = -5000  # $50 debt
    await session.flush()

    # Get the linked CC envelope (should have $0 balance initially)
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == UUID(cc_account_id))
    )
    cc_envelope = result.scalar_one()
    assert cc_envelope.current_balance == 0

    # Unfunded debt should be $50 (full debt is unfunded)
    unfunded = await calculate_unfunded_cc_debt(session, budget.id)
    assert unfunded == 5000, f"Expected $50 unfunded debt, got {unfunded}"

    # Now add $20 to the CC envelope
    cc_envelope.current_balance = 2000  # $20
    await session.flush()

    # Unfunded debt should now be $30 ($50 debt - $20 covered)
    unfunded = await calculate_unfunded_cc_debt(session, budget.id)
    assert unfunded == 3000, f"Expected $30 unfunded debt, got {unfunded}"

    # Fully fund the debt
    cc_envelope.current_balance = 5000  # $50
    await session.flush()

    # Unfunded debt should be $0
    unfunded = await calculate_unfunded_cc_debt(session, budget.id)
    assert unfunded == 0, f"Expected $0 unfunded debt, got {unfunded}"


async def test_envelope_summary_endpoint(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test the /envelopes/summary endpoint returns correct data."""
    from uuid import UUID

    from src.accounts.models import Account, AccountType

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account with $200
    checking = Account(
        budget_id=budget.id,
        name="Summary Test Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=20000,  # $200
    )
    session.add(checking)
    await session.flush()

    # Create an envelope with $150 balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Summary Test Envelope",
        current_balance=15000,  # $150
    )
    session.add(envelope)
    await session.flush()

    # Create a CC account via API
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Summary Test CC",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Set the CC account debt directly (simulating existing debt)
    result = await session.execute(
        select(Account).where(Account.id == UUID(cc_account_id))
    )
    cc_account = result.scalar_one()
    cc_account.cleared_balance = -3000  # $30 debt
    await session.flush()

    # Get the summary
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/envelopes/summary"
    )
    assert response.status_code == 200
    data = response.json()

    # Ready to Assign = $200 (checking) - $150 (envelope) - $0 (CC envelope) = $50
    assert data["ready_to_assign"] == 5000, (
        f"Expected $50 ready to assign, got {data['ready_to_assign']}"
    )

    # Unfunded CC debt = $30 (CC envelope has $0)
    assert data["unfunded_cc_debt"] == 3000, (
        f"Expected $30 unfunded debt, got {data['unfunded_cc_debt']}"
    )
