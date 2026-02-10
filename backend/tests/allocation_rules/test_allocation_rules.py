"""CRUD tests for allocation rules."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.users.models import User


async def test_create_allocation_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create an allocation rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Savings", target_balance=100000)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
            "name": "Save $500",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["envelope_id"] == str(envelope.id)
    assert data["priority"] == 1
    assert data["rule_type"] == "fixed"
    assert data["amount"] == 50000
    assert data["is_active"] is True
    assert data["name"] == "Save $500"


async def test_create_percentage_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create a percentage-based rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Savings")
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "percentage",
            "amount": 2000,  # 20%
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_type"] == "percentage"
    assert data["amount"] == 2000


async def test_create_fill_to_target_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create a fill_to_target rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id, name="Emergency Fund", target_balance=1000000
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fill_to_target",
            "name": "Build Emergency Fund",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_type"] == "fill_to_target"


async def test_create_remainder_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create a remainder rule with weight."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Fun Money")
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 4000,  # 40% weight
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_type"] == "remainder"
    assert data["amount"] == 4000


async def test_list_allocation_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can list allocation rules ordered by priority."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope1 = Envelope(budget_id=budget.id, name="First")
    envelope2 = Envelope(budget_id=budget.id, name="Second")
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    # Create rules in non-priority order
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope2.id),
            "priority": 2,
            "rule_type": "fixed",
            "amount": 2000,
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope1.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should be ordered by priority
    assert data[0]["priority"] == 1
    assert data[1]["priority"] == 2


async def test_list_active_rules_only(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can filter to only active rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test")
    session.add(envelope)
    await session.flush()

    # Create active and inactive rules
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
            "is_active": True,
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 2,
            "rule_type": "fixed",
            "amount": 2000,
            "is_active": False,
        },
    )

    # List all rules
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules"
    )
    assert len(response.json()) == 2

    # List active only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules?active_only=true"
    )
    assert len(response.json()) == 1
    assert response.json()[0]["is_active"] is True


async def test_get_allocation_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can get a single allocation rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test")
    session.add(envelope)
    await session.flush()

    create_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )
    rule_id = create_response.json()["id"]

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}"
    )
    assert response.status_code == 200
    assert response.json()["id"] == rule_id


async def test_get_allocation_rule_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Returns 404 for non-existent rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_allocation_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can update an allocation rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test")
    session.add(envelope)
    await session.flush()

    create_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )
    rule_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}",
        json={
            "amount": 2000,
            "name": "Updated Name",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 2000
    assert data["name"] == "Updated Name"


async def test_update_allocation_rule_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can change the target envelope of a rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope1 = Envelope(budget_id=budget.id, name="First")
    envelope2 = Envelope(budget_id=budget.id, name="Second")
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    create_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope1.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )
    rule_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}",
        json={"envelope_id": str(envelope2.id)},
    )
    assert response.status_code == 200
    assert response.json()["envelope_id"] == str(envelope2.id)


async def test_delete_allocation_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can delete an allocation rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test")
    session.add(envelope)
    await session.flush()

    create_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )
    rule_id = create_response.json()["id"]

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}"
    )
    assert response.status_code == 204

    # Verify deleted
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}"
    )
    assert response.status_code == 404


async def test_create_rule_invalid_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot create rule for non-existent envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": "00000000-0000-0000-0000-000000000000",
            "priority": 1,
            "rule_type": "fixed",
            "amount": 1000,
        },
    )
    assert response.status_code == 404


async def test_create_period_cap_rule(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create a period_cap rule."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Monthly Cap Test")
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,  # $100
            "cap_period_value": 1,
            "cap_period_unit": "month",
            "name": "Monthly $100 Cap",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_type"] == "period_cap"
    assert data["amount"] == 10000
    assert data["cap_period_value"] == 1
    assert data["cap_period_unit"] == "month"
    assert data["name"] == "Monthly $100 Cap"


async def test_create_duplicate_period_cap_same_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot create a second period_cap rule on the same envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Capped Envelope")
    session.add(envelope)
    await session.flush()

    # Create first period_cap rule
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )
    assert response.status_code == 201

    # Try to create a second period_cap rule on the same envelope
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 20000,
            "cap_period_value": 1,
            "cap_period_unit": "week",
        },
    )
    assert response.status_code == 400
    assert "period_cap" in response.json()["detail"].lower()


async def test_create_period_cap_on_different_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can create period_cap rules on different envelopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope1 = Envelope(budget_id=budget.id, name="Envelope A")
    envelope2 = Envelope(budget_id=budget.id, name="Envelope B")
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope1.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )
    assert response.status_code == 201

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope2.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 20000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )
    assert response.status_code == 201


async def test_change_fixed_to_period_cap_when_cap_exists(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot change a fixed rule to period_cap when one already exists."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Has Cap")
    session.add(envelope)
    await session.flush()

    # Create a period_cap rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )

    # Create a fixed rule on same envelope
    create_resp = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 5000,
        },
    )
    fixed_rule_id = create_resp.json()["id"]

    # Try to change fixed -> period_cap
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{fixed_rule_id}",
        json={
            "rule_type": "period_cap",
            "amount": 20000,
            "cap_period_value": 1,
            "cap_period_unit": "week",
        },
    )
    assert response.status_code == 400


async def test_update_existing_period_cap_rule_allowed(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can update fields on the existing period_cap rule itself."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Cap Update")
    session.add(envelope)
    await session.flush()

    create_resp = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )
    rule_id = create_resp.json()["id"]

    # Update the same rule's amount
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}",
        json={"amount": 20000},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 20000


async def test_move_period_cap_to_envelope_that_has_one(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot move a period_cap rule to an envelope that already has one."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope1 = Envelope(budget_id=budget.id, name="Env A")
    envelope2 = Envelope(budget_id=budget.id, name="Env B")
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    # Create period_cap on envelope1
    create_resp = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope1.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            "cap_period_value": 1,
            "cap_period_unit": "month",
        },
    )
    rule_id = create_resp.json()["id"]

    # Create period_cap on envelope2
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope2.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 20000,
            "cap_period_value": 1,
            "cap_period_unit": "week",
        },
    )

    # Try to move envelope1's cap to envelope2
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}",
        json={"envelope_id": str(envelope2.id)},
    )
    assert response.status_code == 400


async def test_create_period_cap_without_unit_fails(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Creating period_cap rule without cap_period_unit should fail."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Cap No Unit")
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 10000,
            # Missing cap_period_unit
        },
    )
    assert response.status_code == 422


async def test_create_period_cap_without_amount_fails(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Creating period_cap rule with zero amount should fail."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Cap No Amount")
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 0,
            "cap_period_unit": "month",
        },
    )
    assert response.status_code == 422


async def test_period_cap_fields_in_response(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Period cap fields should appear in GET response."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Cap Response Test")
    session.add(envelope)
    await session.flush()

    create_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 0,
            "rule_type": "period_cap",
            "amount": 50000,
            "cap_period_value": 3,
            "cap_period_unit": "month",
            "name": "Quarterly Cap",
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["id"]

    # GET the rule and verify fields
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocation-rules/{rule_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rule_type"] == "period_cap"
    assert data["amount"] == 50000
    assert data["cap_period_value"] == 3
    assert data["cap_period_unit"] == "month"
    assert data["name"] == "Quarterly Cap"
