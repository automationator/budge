"""Tests for budget update and delete endpoints."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.users.models import User
from tests import utils

# Update budget tests


async def test_update_budget_owner(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Owner can rename their budget."""
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()
    old_name = budget.name

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}",
        json={"name": "Renamed Budget"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renamed Budget"
    assert data["id"] == str(budget.id)

    # Verify the change in database
    await session.refresh(budget)
    assert budget.name == "Renamed Budget"
    assert budget.name != old_name


async def test_update_budget_admin(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Admin can rename the budget."""
    # Get test_user's budget
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

    response = await client.patch(
        f"/api/v1/budgets/{budget.id}",
        json={"name": "Admin Renamed Budget"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Admin Renamed Budget"


async def test_update_budget_member_forbidden(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Member (non-admin) cannot rename the budget."""
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as regular member
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

    response = await client.patch(
        f"/api/v1/budgets/{budget.id}",
        json={"name": "Should Fail"},
    )
    assert response.status_code == 403


async def test_update_budget_unauthorized(client: AsyncClient) -> None:
    """Unauthenticated request fails."""
    response = await client.patch(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000",
        json={"name": "New Name"},
    )
    assert response.status_code == 401


async def test_update_budget_not_found(
    authenticated_client: AsyncClient,
) -> None:
    """Non-existent budget returns 404."""
    response = await authenticated_client.patch(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000",
        json={"name": "New Name"},
    )
    assert response.status_code == 404


async def test_update_budget_empty_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Empty name is rejected."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}",
        json={"name": ""},
    )
    assert response.status_code == 422


# Delete budget tests


async def test_delete_budget_owner(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Owner can delete their budget with correct password."""
    # Create a new budget to delete (keep the original)
    new_budget = Budget(name="Budget to Delete", owner_id=test_user.id)
    session.add(new_budget)
    await session.flush()

    membership = BudgetMembership(
        user_id=test_user.id,
        budget_id=new_budget.id,
        role=BudgetRole.OWNER,
    )
    session.add(membership)
    await session.flush()

    budget_id = new_budget.id

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget_id}",
        json={"password": utils.TEST_USER_PASSWORD},
    )
    assert response.status_code == 204

    # Verify budget is deleted
    result = await session.execute(select(Budget).where(Budget.id == budget_id))
    assert result.scalar_one_or_none() is None


async def test_delete_budget_wrong_password(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Wrong password is rejected."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}",
        json={"password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "password" in response.json()["detail"].lower()


async def test_delete_budget_admin_forbidden(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Admin cannot delete the budget (only owner)."""
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

    response = await client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}",
        json={"password": utils.TEST_USER2_PASSWORD},
    )
    assert response.status_code == 403


async def test_delete_budget_cascades_data(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a budget cascades to all associated data."""
    # Create a new budget with data
    new_budget = Budget(name="Budget with Data", owner_id=test_user.id)
    session.add(new_budget)
    await session.flush()

    membership = BudgetMembership(
        user_id=test_user.id,
        budget_id=new_budget.id,
        role=BudgetRole.OWNER,
    )
    session.add(membership)

    # Add an account
    account = Account(
        name="Test Account",
        budget_id=new_budget.id,
        account_type="checking",
        cleared_balance=1000,
    )
    session.add(account)
    await session.flush()

    budget_id = new_budget.id
    account_id = account.id

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget_id}",
        json={"password": utils.TEST_USER_PASSWORD},
    )
    assert response.status_code == 204

    # Verify budget and account are deleted
    result = await session.execute(select(Budget).where(Budget.id == budget_id))
    assert result.scalar_one_or_none() is None

    result = await session.execute(select(Account).where(Account.id == account_id))
    assert result.scalar_one_or_none() is None


async def test_delete_budget_user_ends_with_zero_budgets(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """User can delete their last budget and end up with zero budgets."""
    # Get user's only budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()
    budget_id = budget.id

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget_id}",
        json={"password": utils.TEST_USER_PASSWORD},
    )
    assert response.status_code == 204

    # Verify user has no budgets
    result = await session.execute(
        select(BudgetMembership).where(BudgetMembership.user_id == test_user.id)
    )
    memberships = list(result.scalars().all())
    assert len(memberships) == 0


async def test_delete_budget_not_found(
    authenticated_client: AsyncClient,
) -> None:
    """Non-existent budget returns 404."""
    response = await authenticated_client.request(
        "DELETE",
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000",
        json={"password": utils.TEST_USER_PASSWORD},
    )
    assert response.status_code == 404


async def test_delete_budget_unauthorized(client: AsyncClient) -> None:
    """Unauthenticated request fails."""
    response = await client.request(
        "DELETE",
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000",
        json={"password": "password"},
    )
    assert response.status_code == 401
