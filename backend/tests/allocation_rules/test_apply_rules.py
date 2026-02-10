"""Tests for applying allocation rules to unallocated balance."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.envelopes.service import (
    calculate_unallocated_balance,
    ensure_unallocated_envelope,
)
from src.users.models import User


async def _create_budget_account_with_balance(
    session: AsyncSession, budget_id, balance: int
) -> Account:
    """Helper to create a budget account with the given balance.

    This creates unallocated funds since unallocated = account balance - envelope balance.
    Also ensures the unallocated envelope exists for API endpoints to work.
    """
    # Ensure unallocated envelope exists (API endpoints check for it)
    await ensure_unallocated_envelope(session, budget_id)

    account = Account(
        budget_id=budget_id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=balance,
    )
    session.add(account)
    await session.flush()
    return account


async def test_apply_rules_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules distributes unallocated money to envelopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money (this creates unallocated funds)
    await _create_budget_account_with_balance(session, budget.id, 100000)  # $1000

    # Verify unallocated balance
    unallocated_balance = await calculate_unallocated_balance(session, budget.id)
    assert unallocated_balance == 100000

    # Create target envelope
    savings = Envelope(budget_id=budget.id, name="Savings")
    session.add(savings)
    await session.flush()

    # Create a fixed rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,  # $500
            "name": "Monthly Savings",
        },
    )

    # Apply rules
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["initial_unallocated"] == 100000
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 50000
    assert data["allocations"][0]["envelope_name"] == "Savings"
    assert data["allocations"][0]["rule_name"] == "Monthly Savings"
    assert data["final_unallocated"] == 50000


async def test_apply_rules_updates_envelope_balances(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules actually updates envelope balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    await _create_budget_account_with_balance(session, budget.id, 100000)  # $1000

    # Create target envelope
    rent = Envelope(budget_id=budget.id, name="Rent")
    session.add(rent)
    await session.flush()

    initial_rent_balance = rent.current_balance

    # Create a fixed rule for $400
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(rent.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 40000,
        },
    )

    # Apply rules
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )
    assert response.status_code == 201

    # Refresh from database
    await session.refresh(rent)

    # Check rent balance updated
    assert rent.current_balance == initial_rent_balance + 40000

    # Check unallocated balance (calculated dynamically)
    unallocated = await calculate_unallocated_balance(session, budget.id)
    assert unallocated == 60000  # $1000 - $400


async def test_apply_rules_multiple_envelopes(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules distributes to multiple envelopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    await _create_budget_account_with_balance(session, budget.id, 100000)  # $1000

    # Create target envelopes
    rent = Envelope(budget_id=budget.id, name="Rent")
    savings = Envelope(budget_id=budget.id, name="Savings")
    fun = Envelope(budget_id=budget.id, name="Fun")
    session.add(rent)
    session.add(savings)
    session.add(fun)
    await session.flush()

    # Create rules
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(rent.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 2,
            "rule_type": "percentage",
            "amount": 2000,  # 20%
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(fun.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # Apply rules
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["initial_unallocated"] == 100000
    assert len(data["allocations"]) == 3

    # Build map of allocations
    amounts = {a["envelope_name"]: a["amount"] for a in data["allocations"]}
    # Rent gets $500 (fixed)
    assert amounts["Rent"] == 50000
    # Savings gets 20% of remaining $500 = $100
    assert amounts["Savings"] == 10000
    # Fun gets remainder = $400
    assert amounts["Fun"] == 40000
    assert data["final_unallocated"] == 0


async def test_apply_rules_no_unallocated_money(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules fails when no unallocated money available."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Don't create any budget accounts - no unallocated funds
    # (unallocated = 0 - 0 = 0)

    # Create a rule
    envelope = Envelope(budget_id=budget.id, name="Savings")
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
        },
    )

    # Apply rules should fail
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 400
    assert "No unallocated money" in response.json()["detail"]


async def test_apply_rules_no_active_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules fails when no active rules exist."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    await _create_budget_account_with_balance(session, budget.id, 100000)

    # No rules created

    # Apply rules should fail
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 400
    assert "No active allocation rules" in response.json()["detail"]


async def test_apply_rules_inactive_rules_ignored(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules ignores inactive rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    await _create_budget_account_with_balance(session, budget.id, 100000)

    # Create envelopes
    active_env = Envelope(budget_id=budget.id, name="Active")
    inactive_env = Envelope(budget_id=budget.id, name="Inactive")
    session.add(active_env)
    session.add(inactive_env)
    await session.flush()

    # Create inactive rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(inactive_env.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
            "is_active": False,
        },
    )
    # Create active rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(active_env.id),
            "priority": 2,
            "rule_type": "fixed",
            "amount": 30000,
            "is_active": True,
        },
    )

    # Apply rules
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 201
    data = response.json()
    # Only active rule should be applied
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_name"] == "Active"
    assert data["allocations"][0]["amount"] == 30000
    assert data["final_unallocated"] == 70000


async def test_apply_rules_fill_to_target(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules with fill_to_target respects envelope target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    # Total unallocated needs to be $1000, and envelope will have $900
    # So account needs $1000 + $900 = $1900
    await _create_budget_account_with_balance(session, budget.id, 190000)  # $1900

    # Create envelope near target
    envelope = Envelope(
        budget_id=budget.id,
        name="Emergency",
        current_balance=90000,  # $900
        target_balance=100000,  # $1000 target
    )
    session.add(envelope)
    await session.flush()

    # Verify unallocated: $1900 - $900 = $1000
    unallocated = await calculate_unallocated_balance(session, budget.id)
    assert unallocated == 100000

    # Create fill_to_target rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fill_to_target",
        },
    )

    # Apply rules
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 201
    data = response.json()
    # Should only allocate $100 to reach target
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 10000
    assert data["final_unallocated"] == 90000


async def test_apply_rules_all_at_target_returns_error(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules fails when all envelopes are at target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    # Envelope has $1000 balance, we want $1000 unallocated, so account needs $2000
    await _create_budget_account_with_balance(session, budget.id, 200000)  # $2000

    # Create envelope already at target
    envelope = Envelope(
        budget_id=budget.id,
        name="Full",
        current_balance=100000,  # $1000
        target_balance=100000,  # $1000 target - already at target
    )
    session.add(envelope)
    await session.flush()

    # Verify unallocated: $2000 - $1000 = $1000
    unallocated = await calculate_unallocated_balance(session, budget.id)
    assert unallocated == 100000

    # Create fill_to_target rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fill_to_target",
        },
    )

    # Apply rules - should fail because no allocations would be made
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 400
    assert "No active allocation rules" in response.json()["detail"]


async def test_apply_rules_negative_unallocated_fails(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules fails when unallocated balance is negative."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create scenario with negative unallocated:
    # Account balance $0, envelope balance $500
    # Unallocated = $0 - $500 = -$500
    envelope = Envelope(budget_id=budget.id, name="Overspent", current_balance=50000)
    session.add(envelope)
    await session.flush()

    # Verify negative unallocated
    unallocated = await calculate_unallocated_balance(session, budget.id)
    assert unallocated == -50000

    # Create a rule (for a different envelope)
    savings = Envelope(budget_id=budget.id, name="Savings")
    session.add(savings)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
        },
    )

    # Apply rules should fail
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 400
    assert "No unallocated money" in response.json()["detail"]


async def test_apply_rules_response_includes_envelope_names(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Apply rules response includes envelope names for display."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with money
    await _create_budget_account_with_balance(session, budget.id, 100000)

    # Create envelope with specific name
    envelope = Envelope(budget_id=budget.id, name="Monthly Groceries")
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
            "name": "Grocery Budget",
        },
    )

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/apply",
    )

    assert response.status_code == 201
    data = response.json()
    alloc = data["allocations"][0]
    assert alloc["envelope_name"] == "Monthly Groceries"
    assert alloc["envelope_id"] == str(envelope.id)
    assert alloc["rule_name"] == "Grocery Budget"
