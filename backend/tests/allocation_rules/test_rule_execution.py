"""Tests for allocation rule execution logic."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.users.models import User


async def test_fixed_rule_execution(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Fixed rule allocates exact amount."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Rent")
    session.add(envelope)
    await session.flush()

    # Create fixed rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 150000,  # $1500
            "name": "Rent",
        },
    )

    # Preview with $2000 income
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 200000},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 150000
    assert data["unallocated"] == 50000


async def test_fixed_rule_exceeds_remaining(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Fixed rule only allocates what's available if income < amount."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Rent")
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 150000,
        },
    )

    # Preview with only $1000 income
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    assert data["allocations"][0]["amount"] == 100000  # Only gets what's available
    assert data["unallocated"] == 0


async def test_percentage_rule_execution(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Percentage rule allocates correct percentage."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Savings")
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "percentage",
            "amount": 2000,  # 20%
        },
    )

    # Preview with $1000 income
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    assert data["allocations"][0]["amount"] == 20000  # 20% of 100000
    assert data["unallocated"] == 80000


async def test_fill_to_target_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Fill to target allocates until target reached."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Emergency Fund",
        current_balance=80000,  # $800
        target_balance=100000,  # $1000
    )
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fill_to_target",
        },
    )

    # Preview with $500 income - only needs $200 to reach target
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 50000},
    )
    data = response.json()
    assert data["allocations"][0]["amount"] == 20000  # Only $200 needed
    assert data["unallocated"] == 30000


async def test_fill_to_target_already_met(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Fill to target skips if already at or above target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(
        budget_id=budget.id,
        name="Emergency Fund",
        current_balance=100000,
        target_balance=100000,  # Already at target
    )
    session.add(envelope)
    await session.flush()

    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fill_to_target",
        },
    )

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 50000},
    )
    data = response.json()
    assert len(data["allocations"]) == 0  # Nothing allocated
    assert data["unallocated"] == 50000


async def test_remainder_single(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Single remainder rule gets all remaining."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    fixed_env = Envelope(budget_id=budget.id, name="Fixed")
    remainder_env = Envelope(budget_id=budget.id, name="Remainder")
    session.add(fixed_env)
    session.add(remainder_env)
    await session.flush()

    # Fixed rule first
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(fixed_env.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,
        },
    )
    # Remainder rule second
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(remainder_env.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 10000,  # Weight (doesn't matter with single remainder)
        },
    )

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    assert len(data["allocations"]) == 2
    assert data["allocations"][0]["amount"] == 50000  # Fixed
    assert data["allocations"][1]["amount"] == 50000  # Remainder gets rest
    assert data["unallocated"] == 0


async def test_remainder_weighted_split(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Multiple remainder rules split by weight."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    vacation = Envelope(budget_id=budget.id, name="Vacation")
    fun = Envelope(budget_id=budget.id, name="Fun")
    session.add(vacation)
    session.add(fun)
    await session.flush()

    # 60% to vacation
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(vacation.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 6000,  # 60% weight
        },
    )
    # 40% to fun
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(fun.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 4000,  # 40% weight
        },
    )

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    assert len(data["allocations"]) == 2
    # Note: Order might vary, so check both
    amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    assert amounts[str(vacation.id)] == 60000  # 60%
    assert amounts[str(fun.id)] == 40000  # 40%
    assert data["unallocated"] == 0


async def test_priority_ordering(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Rules execute in priority order."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    first = Envelope(budget_id=budget.id, name="First")
    second = Envelope(budget_id=budget.id, name="Second")
    session.add(first)
    session.add(second)
    await session.flush()

    # Create in reverse priority order
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(second.id),
            "priority": 2,
            "rule_type": "fixed",
            "amount": 100000,  # Would take all if first
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(first.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 60000,
        },
    )

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    # First priority gets its full amount, second gets remainder
    amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    assert amounts[str(first.id)] == 60000
    assert amounts[str(second.id)] == 40000  # Only what's left


async def test_inactive_rules_skipped(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Inactive rules are not applied."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    active_env = Envelope(budget_id=budget.id, name="Active")
    inactive_env = Envelope(budget_id=budget.id, name="Inactive")
    session.add(active_env)
    session.add(inactive_env)
    await session.flush()

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

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(active_env.id)
    assert data["allocations"][0]["amount"] == 30000
    assert data["unallocated"] == 70000


async def test_mixed_rule_types(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Complex scenario with multiple rule types."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    emergency = Envelope(
        budget_id=budget.id,
        name="Emergency",
        current_balance=90000,
        target_balance=100000,
    )
    rent = Envelope(budget_id=budget.id, name="Rent")
    savings = Envelope(budget_id=budget.id, name="Savings")
    vacation = Envelope(budget_id=budget.id, name="Vacation")
    session.add(emergency)
    session.add(rent)
    session.add(savings)
    session.add(vacation)
    await session.flush()

    # Priority 1: Fill emergency fund (needs $100)
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(emergency.id),
            "priority": 1,
            "rule_type": "fill_to_target",
        },
    )
    # Priority 2: Fixed rent
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(rent.id),
            "priority": 2,
            "rule_type": "fixed",
            "amount": 150000,
        },
    )
    # Priority 3: 20% to savings
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 3,
            "rule_type": "percentage",
            "amount": 2000,  # 20%
        },
    )
    # Priority 100: Remainder to vacation
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(vacation.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # $3000 income
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 300000},
    )
    data = response.json()

    amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    # 1. Emergency: needs $100 to reach target
    assert amounts[str(emergency.id)] == 10000
    # Remaining: $3000 - $100 = $2900
    # 2. Rent: $1500
    assert amounts[str(rent.id)] == 150000
    # Remaining: $2900 - $1500 = $1400
    # 3. Savings: 20% of $1400 = $280
    assert amounts[str(savings.id)] == 28000
    # Remaining: $1400 - $280 = $1120
    # 4. Vacation: remainder = $1120
    assert amounts[str(vacation.id)] == 112000
    assert data["unallocated"] == 0


async def test_fixed_rule_respect_target(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Fixed rule with respect_target stops at envelope target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Envelope with $800 current, $1000 target = only $200 headroom
    envelope = Envelope(
        budget_id=budget.id,
        name="Savings",
        current_balance=80000,
        target_balance=100000,
    )
    session.add(envelope)
    await session.flush()

    # Fixed rule for $500, but with respect_target enabled
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "fixed",
            "amount": 50000,  # $500
            "respect_target": True,
        },
    )

    # Preview with $1000 income
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    # Only allocates $200 (headroom), not $500
    assert data["allocations"][0]["amount"] == 20000
    assert data["unallocated"] == 80000


async def test_percentage_rule_respect_target(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Percentage rule with respect_target stops at envelope target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Envelope with $900 current, $1000 target = only $100 headroom
    envelope = Envelope(
        budget_id=budget.id,
        name="Savings",
        current_balance=90000,
        target_balance=100000,
    )
    session.add(envelope)
    await session.flush()

    # 50% rule, but with respect_target enabled
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(envelope.id),
            "priority": 1,
            "rule_type": "percentage",
            "amount": 5000,  # 50%
            "respect_target": True,
        },
    )

    # Preview with $1000 income - 50% would be $500
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    # Only allocates $100 (headroom), not $500
    assert data["allocations"][0]["amount"] == 10000
    assert data["unallocated"] == 90000


async def test_remainder_rule_respect_target(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Remainder rule with respect_target stops at envelope target."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Envelope with $900 current, $1000 target = only $100 headroom
    limited = Envelope(
        budget_id=budget.id,
        name="Limited",
        current_balance=90000,
        target_balance=100000,
    )
    unlimited = Envelope(budget_id=budget.id, name="Unlimited")
    session.add(limited)
    session.add(unlimited)
    await session.flush()

    # Limited remainder with respect_target
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(limited.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 5000,  # 50% weight
            "respect_target": True,
        },
    )
    # Unlimited remainder (no respect_target)
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(unlimited.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 5000,  # 50% weight
            "respect_target": False,
        },
    )

    # Preview with $1000 income
    # Without respect_target: $500 each
    # With respect_target on limited: $100 to limited, rest to unlimited
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    # Limited gets $100 (its headroom)
    assert amounts[str(limited.id)] == 10000
    # Unlimited gets the rest ($900)
    assert amounts[str(unlimited.id)] == 90000
    assert data["unallocated"] == 0


async def test_remainder_respect_target_all_limited(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """When all remainder rules have respect_target, excess is unallocated."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Both envelopes nearly full
    env1 = Envelope(
        budget_id=budget.id,
        name="Env1",
        current_balance=95000,
        target_balance=100000,  # $50 headroom
    )
    env2 = Envelope(
        budget_id=budget.id,
        name="Env2",
        current_balance=97000,
        target_balance=100000,  # $30 headroom
    )
    session.add(env1)
    session.add(env2)
    await session.flush()

    # Both with respect_target
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(env1.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 5000,
            "respect_target": True,
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(env2.id),
            "priority": 100,
            "rule_type": "remainder",
            "amount": 5000,
            "respect_target": True,
        },
    )

    # Preview with $1000 income - but only $80 total headroom
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules/preview",
        json={"amount": 100000},
    )
    data = response.json()
    amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    # Each gets their headroom
    assert amounts[str(env1.id)] == 5000  # $50
    assert amounts[str(env2.id)] == 3000  # $30
    # Rest is unallocated
    assert data["unallocated"] == 92000  # $920
