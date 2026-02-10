from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.users.models import User
from tests import utils

# Create budget tests


async def test_create_budget(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    response = await authenticated_client.post(
        "/api/v1/budgets",
        json={"name": "My New Budget"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My New Budget"
    assert data["owner_id"] == str(test_user.id)

    # Verify the budget was created in the database
    result = await session.execute(select(Budget).where(Budget.id == data["id"]))
    budget = result.scalar_one()
    assert budget.name == "My New Budget"
    assert budget.owner_id == test_user.id

    # Verify the user is a member with owner role
    result = await session.execute(
        select(BudgetMembership).where(
            BudgetMembership.budget_id == budget.id,
            BudgetMembership.user_id == test_user.id,
        )
    )
    membership = result.scalar_one()
    assert membership.role == BudgetRole.OWNER


async def test_create_budget_unauthorized(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/budgets",
        json={"name": "My New Budget"},
    )
    assert response.status_code == 401


async def test_create_budget_missing_name(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/v1/budgets",
        json={},
    )
    assert response.status_code == 422


async def test_create_budget_empty_name(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/v1/budgets",
        json={"name": ""},
    )
    assert response.status_code == 422


async def test_create_multiple_budgets(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Create first budget
    response1 = await authenticated_client.post(
        "/api/v1/budgets",
        json={"name": "Budget One"},
    )
    assert response1.status_code == 201

    # Create second budget
    response2 = await authenticated_client.post(
        "/api/v1/budgets",
        json={"name": "Budget Two"},
    )
    assert response2.status_code == 201

    # Verify user is now a member of 3 budgets (original + 2 new)
    result = await session.execute(
        select(BudgetMembership).where(BudgetMembership.user_id == test_user.id)
    )
    memberships = list(result.scalars().all())
    assert len(memberships) == 3


# Add member tests


async def test_add_member_by_username(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": utils.TEST_USER2_USERNAME},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == test_user2.username


async def test_add_member_not_budget_member(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Authenticate as test_user2 (not a member of the budget)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"].lower()


async def test_add_member_user_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "nonexistentuser"},
    )
    assert response.status_code == 404


async def test_add_member_already_member(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 to the budget first
    user_budget = BudgetMembership(user_id=test_user2.id, budget_id=budget.id)
    session.add(user_budget)
    await session.flush()

    # Try to add again
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": utils.TEST_USER2_USERNAME},
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


async def test_add_member_budget_not_found(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 404


async def test_add_member_unauthorized(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 401


async def test_add_member_missing_username(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={},
    )
    assert response.status_code == 422


# Remove member tests


async def test_remove_member_by_username(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 to the budget first
    user_budget = BudgetMembership(user_id=test_user2.id, budget_id=budget.id)
    session.add(user_budget)
    await session.flush()

    # Remove test_user2 from the budget by username
    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": test_user2.username},
    )
    assert response.status_code == 204

    # Verify the membership is gone
    result = await session.execute(
        select(BudgetMembership).where(
            BudgetMembership.user_id == test_user2.id,
            BudgetMembership.budget_id == budget.id,
        )
    )
    assert result.scalar_one_or_none() is None


async def test_remove_member_not_budget_member(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Authenticate as test_user2 (not a member of the budget)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": test_user.username},
    )
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"].lower()


async def test_remove_member_cannot_remove_owner(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Try to remove the owner (themselves)
    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": test_user.username},
    )
    assert response.status_code == 400
    assert "owner" in response.json()["detail"].lower()


async def test_remove_member_not_a_member(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Try to remove test_user2 who is not a member
    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": test_user2.username},
    )
    assert response.status_code == 400
    assert "not a member" in response.json()["detail"].lower()


async def test_remove_member_budget_not_found(
    authenticated_client: AsyncClient,
    test_user: User,
) -> None:
    response = await authenticated_client.request(
        "DELETE",
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/members",
        json={"username": test_user.username},
    )
    assert response.status_code == 404


async def test_remove_member_user_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "nonexistentuser"},
    )
    assert response.status_code == 404


async def test_remove_member_unauthorized(client: AsyncClient) -> None:
    response = await client.request(
        "DELETE",
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 401


async def test_remove_member_missing_username(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members",
        json={},
    )
    assert response.status_code == 422
