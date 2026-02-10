"""Integration tests for allocation rules with transactions."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.users.models import User


async def test_income_defaults_to_unallocated_when_no_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Income transaction without explicit allocations defaults to Unallocated envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    savings = Envelope(budget_id=budget.id, name="Savings")
    session.add(account)
    session.add(payee)
    session.add(savings)
    await session.flush()

    # Create allocation rule: 100% to savings (rules are no longer auto-applied)
    rule_response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "remainder",
            "amount": 10000,  # 100% weight
        },
    )
    assert rule_response.status_code == 201

    # Create income transaction without allocations
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 200000,  # $2000 income
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify allocations default to Unallocated envelope (rules not auto-applied)
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 200000
    # Should not have a rule_id since not auto-applied
    assert data["allocations"][0]["allocation_rule_id"] is None

    # Verify it's allocated to the Unallocated envelope
    envelope_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = envelope_result.scalar_one()
    assert data["allocations"][0]["envelope_id"] == str(unallocated.id)

    # Savings envelope should be unchanged
    await session.refresh(savings)
    assert savings.current_balance == 0


async def test_skip_allocation_rules_flag(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """skip_allocation_rules=true bypasses automatic rule application."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    savings = Envelope(budget_id=budget.id, name="Savings")
    other = Envelope(budget_id=budget.id, name="Other")
    session.add(account)
    session.add(payee)
    session.add(savings)
    session.add(other)
    await session.flush()

    # Create allocation rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # Create income with skip_allocation_rules and manual allocation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 200000,
            "skip_allocation_rules": True,
            "allocations": [
                {"envelope_id": str(other.id), "amount": 200000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify manual allocation was used, not rule
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(other.id)
    assert data["allocations"][0]["allocation_rule_id"] is None


async def test_manual_allocations_override_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Explicit allocations in request override automatic rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    savings = Envelope(budget_id=budget.id, name="Savings")
    other = Envelope(budget_id=budget.id, name="Other")
    session.add(account)
    session.add(payee)
    session.add(savings)
    session.add(other)
    await session.flush()

    # Create allocation rule (would go to savings)
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # Create income with explicit allocations (to other, not savings)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 200000,
            "allocations": [
                {"envelope_id": str(other.id), "amount": 200000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify explicit allocation was used
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(other.id)


async def test_expense_does_not_trigger_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Expense transactions (negative amount) do not trigger allocation rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Store")
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=100000)
    savings = Envelope(budget_id=budget.id, name="Savings")
    session.add(account)
    session.add(payee)
    session.add(groceries)
    session.add(savings)
    await session.flush()

    # Create allocation rule (would try to auto-allocate if triggered)
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # Create expense - must provide explicit allocations
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # Expense
            "allocations": [
                {"envelope_id": str(groceries.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify expense went to groceries, not triggered rules
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(groceries.id)


async def test_non_budget_account_skips_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Non-budget accounts don't need allocations (rules not triggered)."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,  # Not a budget account
    )
    payee = Payee(budget_id=budget.id, name="Broker")
    savings = Envelope(budget_id=budget.id, name="Savings")
    session.add(account)
    session.add(payee)
    session.add(savings)
    await session.flush()

    # Create allocation rule
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocation-rules",
        json={
            "envelope_id": str(savings.id),
            "priority": 1,
            "rule_type": "remainder",
            "amount": 10000,
        },
    )

    # Create transaction in non-budget account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 200000,  # Income
        },
    )
    assert response.status_code == 201
    data = response.json()

    # No allocations (non-budget account)
    assert len(data["allocations"]) == 0


async def test_income_no_rules_defaults_to_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Income in budget account with no rules defaults to Unallocated envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    session.add(account)
    session.add(payee)
    await session.flush()

    # No allocation rules defined - transaction should still succeed

    # Create income without allocations - defaults to Unallocated
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 200000,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Should have one allocation to Unallocated envelope
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 200000

    # Verify it's the Unallocated envelope
    envelope_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = envelope_result.scalar_one()
    assert data["allocations"][0]["envelope_id"] == str(unallocated.id)
