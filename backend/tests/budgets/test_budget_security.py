from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.budgets.scopes import BudgetScope
from src.users.models import User


async def test_list_members_as_owner(
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

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Owner should be able to list members
    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/members")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # owner + member

    # Verify both users are in the list
    usernames = {m["username"] for m in data}
    assert test_user.username in usernames
    assert test_user2.username in usernames

    # Verify roles are correct
    for member in data:
        if member["username"] == test_user.username:
            assert member["role"] == BudgetRole.OWNER
        else:
            assert member["role"] == BudgetRole.MEMBER


async def test_list_members_as_admin(
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

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.ADMIN
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (admin)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Admin should be able to list members
    response = await client.get(f"/api/v1/budgets/{budget.id}/members")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_list_members_as_member_forbidden(
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

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Member should NOT be able to list members (no members:read scope)
    response = await client.get(f"/api/v1/budgets/{budget.id}/members")
    assert response.status_code == 403


async def test_list_members_not_budget_member(
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

    # Authenticate as test_user2 (not a member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Non-member should NOT be able to list members
    response = await client.get(f"/api/v1/budgets/{budget.id}/members")
    assert response.status_code == 403


async def test_admin_can_read_budget_members(
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

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.ADMIN
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (admin)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Admin should be able to read other member's scopes
    response = await client.get(
        f"/api/v1/budgets/{budget.id}/members/{test_user.id}/scopes"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == BudgetRole.OWNER


async def test_member_cannot_read_budget_members(
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

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Member should NOT be able to read other member's scopes (no members:read)
    response = await client.get(
        f"/api/v1/budgets/{budget.id}/members/{test_user.id}/scopes"
    )
    assert response.status_code == 403


async def test_member_cannot_add_members(
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

    # Add test_user2 as a member (not admin/owner)
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Member should NOT be able to add members
    response = await client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()


async def test_admin_can_add_members(
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

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.ADMIN
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (admin)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Admin should be able to add members (will fail because user doesn't exist, but not 403)
    response = await client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "nonexistentuser"},
    )
    # Should be 404 (user not found), not 403 (permission denied)
    assert response.status_code == 404


async def test_admin_cannot_manage_roles(
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

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.ADMIN
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (admin)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Admin should NOT be able to manage roles
    response = await client.patch(
        f"/api/v1/budgets/{budget.id}/members/{test_user.id}/role",
        json={"role": "member"},
    )
    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()


async def test_owner_can_update_member_role(
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

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Owner can update the member's role
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/role",
        json={"role": "admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == BudgetRole.ADMIN


async def test_cannot_assign_owner_role(
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

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.MEMBER
    )
    session.add(membership)
    await session.flush()

    # Cannot assign owner role
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/role",
        json={"role": "owner"},
    )
    assert response.status_code == 400
    assert "owner" in response.json()["detail"].lower()


async def test_cannot_modify_owner_role(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Cannot change the owner's role
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/members/{test_user.id}/role",
        json={"role": "admin"},
    )
    assert response.status_code == 400
    assert "owner" in response.json()["detail"].lower()


async def test_add_scope_to_member(
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

    # Add test_user2 as a viewer
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.VIEWER
    )
    session.add(membership)
    await session.flush()

    # Add members:add scope to the viewer
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/scopes",
        json={"scope": BudgetScope.MEMBERS_ADD},
    )
    assert response.status_code == 201
    data = response.json()
    assert BudgetScope.MEMBERS_ADD in data["scope_additions"]
    assert BudgetScope.MEMBERS_ADD in data["effective_scopes"]


async def test_remove_scope_from_admin(
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

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id, budget_id=budget.id, role=BudgetRole.ADMIN
    )
    session.add(membership)
    await session.flush()

    # Remove members:read scope from the admin
    response = await authenticated_client.request(
        "DELETE",
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/scopes",
        json={"scope": BudgetScope.MEMBERS_READ},
    )
    assert response.status_code == 200
    data = response.json()
    assert BudgetScope.MEMBERS_READ in data["scope_removals"]
    assert BudgetScope.MEMBERS_READ not in data["effective_scopes"]


async def test_scope_override_grants_access(
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

    # Add test_user2 as a viewer with members:add scope override
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.VIEWER,
        scope_additions=[BudgetScope.MEMBERS_ADD],
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (viewer with scope override)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Viewer with scope override should be able to add members (will fail because user doesn't exist)
    response = await client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "nonexistentuser"},
    )
    # Should be 404 (user not found), not 403 (permission denied)
    assert response.status_code == 404


async def test_scope_removal_denies_access(
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

    # Add test_user2 as an admin with members:add scope removed
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
        scope_removals=[BudgetScope.MEMBERS_ADD],
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2 (admin with scope removed)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    # Admin with scope removed should NOT be able to add members
    response = await client.post(
        f"/api/v1/budgets/{budget.id}/members",
        json={"username": "someuser"},
    )
    assert response.status_code == 403


async def test_role_change_clears_scope_overrides(
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

    # Add test_user2 as a member with scope overrides
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
        scope_additions=[BudgetScope.MEMBERS_ADD],
        scope_removals=[BudgetScope.BUDGET_READ],
    )
    session.add(membership)
    await session.flush()

    # Change the role
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/role",
        json={"role": "admin"},
    )
    assert response.status_code == 200

    # Verify scope overrides are cleared
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/members/{test_user2.id}/scopes",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == BudgetRole.ADMIN
    assert data["scope_additions"] == []
    assert data["scope_removals"] == []
