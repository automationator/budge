from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.payees.models import Payee
from src.transactions.models import Transaction
from src.users.models import User


async def test_create_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/payees",
        json={"name": "Grocery Store"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Grocery Store"
    assert data["icon"] is None
    assert data["budget_id"] == str(budget.id)


async def test_create_payee_with_icon(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/payees",
        json={
            "name": "Coffee Shop",
            "icon": "☕",
            "description": "Morning coffee spot",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Coffee Shop"
    assert data["icon"] == "☕"
    assert data["description"] == "Morning coffee spot"


async def test_create_duplicate_payee_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create first payee
    payee = Payee(budget_id=budget.id, name="Duplicate Test")
    session.add(payee)
    await session.flush()

    # Try to create payee with same name
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/payees",
        json={"name": "Duplicate Test"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_list_payees(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some payees
    payees = [
        Payee(budget_id=budget.id, name="Payee B"),
        Payee(budget_id=budget.id, name="Payee A"),
        Payee(budget_id=budget.id, name="Payee C"),
    ]
    for p in payees:
        session.add(p)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/payees")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    # Should be ordered by name
    names = [p["name"] for p in data[-3:]]
    assert names == ["Payee A", "Payee B", "Payee C"]


async def test_get_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    payee = Payee(budget_id=budget.id, name="Get Test Payee", icon="🏪")
    session.add(payee)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/payees/{payee.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test Payee"
    assert data["icon"] == "🏪"


async def test_get_payee_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/payees/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    payee = Payee(budget_id=budget.id, name="Update Test")
    session.add(payee)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/payees/{payee.id}",
        json={"name": "Updated Name", "icon": "🎯"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["icon"] == "🎯"


async def test_update_payee_duplicate_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create two payees
    payee1 = Payee(budget_id=budget.id, name="First Payee")
    payee2 = Payee(budget_id=budget.id, name="Second Payee")
    session.add(payee1)
    session.add(payee2)
    await session.flush()

    # Try to rename payee2 to payee1's name
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/payees/{payee2.id}",
        json={"name": "First Payee"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_delete_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    payee = Payee(budget_id=budget.id, name="Delete Test")
    session.add(payee)
    await session.flush()
    payee_id = payee.id

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/payees/{payee_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await session.execute(select(Payee).where(Payee.id == payee_id))
    assert result.scalar_one_or_none() is None


async def test_delete_payee_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/payees/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_delete_payee_with_linked_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot delete a payee that is linked to existing transactions."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an account
    account = Account(
        budget_id=budget.id,
        name="Test Account",
        account_type="checking",
    )
    session.add(account)
    await session.flush()

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Linked Payee")
    session.add(payee)
    await session.flush()

    # Create a transaction that references the payee
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=-5000,
    )
    session.add(transaction)
    await session.flush()

    # Try to delete the payee - should fail with 409 Conflict
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/payees/{payee.id}"
    )
    assert response.status_code == 409
    data = response.json()
    assert "linked to existing transactions" in data["detail"]
    assert "Linked Payee" in data["detail"]


async def test_payee_unauthorized(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/payees"
    )
    assert response.status_code == 401


async def test_payee_not_budget_member(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Authenticate as test_user2 (not a member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/payees")
    assert response.status_code == 403


async def test_member_can_read_payees(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a member
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

    response = await client.get(f"/api/v1/budgets/{budget.id}/payees")
    assert response.status_code == 200


async def test_member_cannot_create_payee(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a member
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
        f"/api/v1/budgets/{budget.id}/payees",
        json={"name": "New Payee"},
    )
    assert response.status_code == 403


async def test_admin_can_create_payee(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as an admin
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
        f"/api/v1/budgets/{budget.id}/payees",
        json={"name": "Admin Created Payee"},
    )
    assert response.status_code == 201


async def test_admin_cannot_delete_payee(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Admin Delete Test")
    session.add(payee)

    # Add test_user2 as an admin
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

    response = await client.delete(f"/api/v1/budgets/{budget.id}/payees/{payee.id}")
    assert response.status_code == 403


async def test_cannot_access_other_budget_payees(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget1 = result.scalar_one()

    # Create a budget for test_user2
    budget2 = Budget(name="Other Budget", owner_id=test_user2.id)
    session.add(budget2)
    await session.flush()

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget2.id,
        role=BudgetRole.OWNER,
    )
    session.add(membership)

    # Create a payee in budget2
    payee = Payee(budget_id=budget2.id, name="Other Budget Payee")
    session.add(payee)
    await session.flush()

    # Try to access budget2's payee from test_user (authenticated_client is test_user)
    response = await authenticated_client.get(f"/api/v1/budgets/{budget2.id}/payees")
    assert response.status_code == 403

    # Try to get specific payee
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget1.id}/payees/{payee.id}"
    )
    assert response.status_code == 404
