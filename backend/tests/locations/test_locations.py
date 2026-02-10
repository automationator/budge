from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.locations.models import Location
from src.transactions.models import Transaction
from src.users.models import User


async def test_create_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/locations",
        json={"name": "New York"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New York"
    assert data["icon"] is None
    assert data["budget_id"] == str(budget.id)


async def test_create_location_with_icon(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/locations",
        json={"name": "Paris", "icon": "🗼", "description": "City of lights"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Paris"
    assert data["icon"] == "🗼"
    assert data["description"] == "City of lights"


async def test_create_duplicate_location_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create first location
    location = Location(budget_id=budget.id, name="Duplicate Test")
    session.add(location)
    await session.flush()

    # Try to create location with same name
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/locations",
        json={"name": "Duplicate Test"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_list_locations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some locations
    locations = [
        Location(budget_id=budget.id, name="Location B"),
        Location(budget_id=budget.id, name="Location A"),
        Location(budget_id=budget.id, name="Location C"),
    ]
    for loc in locations:
        session.add(loc)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/locations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    # Should be ordered by name
    names = [loc["name"] for loc in data[-3:]]
    assert names == ["Location A", "Location B", "Location C"]


async def test_get_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    location = Location(budget_id=budget.id, name="Get Test Location", icon="📍")
    session.add(location)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/locations/{location.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test Location"
    assert data["icon"] == "📍"


async def test_get_location_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/locations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    location = Location(budget_id=budget.id, name="Update Test")
    session.add(location)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/locations/{location.id}",
        json={"name": "Updated Name", "icon": "🌍"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["icon"] == "🌍"


async def test_update_location_duplicate_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create two locations
    location1 = Location(budget_id=budget.id, name="First Location")
    location2 = Location(budget_id=budget.id, name="Second Location")
    session.add(location1)
    session.add(location2)
    await session.flush()

    # Try to rename location2 to location1's name
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/locations/{location2.id}",
        json={"name": "First Location"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_delete_location(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    location = Location(budget_id=budget.id, name="Delete Test")
    session.add(location)
    await session.flush()
    location_id = location.id

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/locations/{location_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await session.execute(select(Location).where(Location.id == location_id))
    assert result.scalar_one_or_none() is None


async def test_delete_location_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/locations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_delete_location_with_transaction_sets_null(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a location linked to a transaction should succeed and set the FK to null."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an account for the transaction
    account = Account(
        budget_id=budget.id,
        name="Test Account for Location",
        account_type="checking",
        include_in_budget=False,
    )
    session.add(account)
    await session.flush()

    # Create a location
    location = Location(budget_id=budget.id, name="Location With Transaction")
    session.add(location)
    await session.flush()
    location_id = location.id

    # Create a transaction linked to the location
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        amount=-1000,
        date=date.today(),
        location_id=location_id,
    )
    session.add(transaction)
    await session.flush()
    transaction_id = transaction.id

    # Delete the location - should succeed (unlike payees which block deletion)
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/locations/{location_id}"
    )
    assert response.status_code == 204

    # Verify the location is gone
    result = await session.execute(select(Location).where(Location.id == location_id))
    assert result.scalar_one_or_none() is None

    # Verify the transaction still exists but location_id is null
    await session.refresh(transaction)
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one()
    assert txn is not None
    assert txn.location_id is None


async def test_location_unauthorized(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/locations"
    )
    assert response.status_code == 401


async def test_location_not_budget_member(
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

    response = await client.get(f"/api/v1/budgets/{budget.id}/locations")
    assert response.status_code == 403


async def test_member_can_read_locations(
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

    response = await client.get(f"/api/v1/budgets/{budget.id}/locations")
    assert response.status_code == 200


async def test_member_cannot_create_location(
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
        f"/api/v1/budgets/{budget.id}/locations",
        json={"name": "New Location"},
    )
    assert response.status_code == 403


async def test_admin_can_create_location(
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
        f"/api/v1/budgets/{budget.id}/locations",
        json={"name": "Admin Created Location"},
    )
    assert response.status_code == 201


async def test_admin_cannot_delete_location(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a location
    location = Location(budget_id=budget.id, name="Admin Delete Test")
    session.add(location)

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

    response = await client.delete(
        f"/api/v1/budgets/{budget.id}/locations/{location.id}"
    )
    assert response.status_code == 403


async def test_cannot_access_other_budget_locations(
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

    # Create a location in budget2
    location = Location(budget_id=budget2.id, name="Other Budget Location")
    session.add(location)
    await session.flush()

    # Try to access budget2's location from test_user (authenticated_client is test_user)
    response = await authenticated_client.get(f"/api/v1/budgets/{budget2.id}/locations")
    assert response.status_code == 403

    # Try to get specific location
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget1.id}/locations/{location.id}"
    )
    assert response.status_code == 404
