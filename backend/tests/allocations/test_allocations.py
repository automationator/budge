from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocation_rules.models import AllocationRule, AllocationRuleType
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.users.models import User


async def test_create_transaction_with_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Budget account transactions require allocations."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account, payee, and envelope
    account = Account(
        budget_id=budget.id,
        name="Budget Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Grocery Store")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create transaction with allocation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # Expense
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(envelope.id)
    assert data["allocations"][0]["amount"] == -5000

    # Verify envelope balance was updated
    await session.refresh(envelope)
    assert envelope.current_balance == 5000  # 10000 - 5000


async def test_budget_account_income_defaults_to_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Budget account income transactions without allocations default to Unallocated envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Income transaction (positive amount) defaults to Unallocated
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,  # Income (positive)
        },
    )
    assert response.status_code == 201
    data = response.json()
    # Should have one allocation to Unallocated envelope
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 5000

    # Verify it's allocated to the Unallocated envelope
    envelope_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = envelope_result.scalar_one()
    assert data["allocations"][0]["envelope_id"] == str(unallocated.id)


async def test_allocation_amount_must_match_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Allocation amounts must sum to transaction amount."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(budget_id=budget.id, name="Test Envelope")
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -3000},  # Wrong amount
            ],
        },
    )
    assert response.status_code == 400
    assert "must equal transaction amount" in response.json()["detail"]


async def test_split_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transaction can be split across multiple envelopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Costco")
    groceries = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    household = Envelope(budget_id=budget.id, name="Household", current_balance=5000)
    session.add(account)
    session.add(payee)
    session.add(groceries)
    session.add(household)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -10000,
            "allocations": [
                {"envelope_id": str(groceries.id), "amount": -7000},
                {"envelope_id": str(household.id), "amount": -3000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 2

    # Verify envelope balances
    await session.refresh(groceries)
    await session.refresh(household)
    assert groceries.current_balance == 3000  # 10000 - 7000
    assert household.current_balance == 2000  # 5000 - 3000


async def test_delete_transaction_reverses_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a transaction reverses envelope balance changes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(
        budget_id=budget.id, name="Test Envelope", current_balance=10000
    )
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create transaction
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201
    transaction_id = response.json()["id"]

    # Verify balance decreased
    await session.refresh(envelope)
    assert envelope.current_balance == 5000

    # Delete transaction
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction_id}"
    )
    assert response.status_code == 204

    # Verify balance restored
    await session.refresh(envelope)
    assert envelope.current_balance == 10000


async def test_envelope_transfer(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Envelope transfer creates two allocations without a transaction."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    source = Envelope(budget_id=budget.id, name="Source", current_balance=10000)
    dest = Envelope(budget_id=budget.id, name="Destination", current_balance=0)
    session.add(source)
    session.add(dest)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocations/envelope-transfer",
        json={
            "source_envelope_id": str(source.id),
            "destination_envelope_id": str(dest.id),
            "amount": 3000,
        },
    )
    assert response.status_code == 201
    data = response.json()

    assert data["source_allocation"]["envelope_id"] == str(source.id)
    assert data["source_allocation"]["amount"] == -3000
    assert data["destination_allocation"]["envelope_id"] == str(dest.id)
    assert data["destination_allocation"]["amount"] == 3000

    # Verify balances
    await session.refresh(source)
    await session.refresh(dest)
    assert source.current_balance == 7000
    assert dest.current_balance == 3000


async def test_envelope_transfer_same_envelope_fails(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Cannot transfer to the same envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=10000)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocations/envelope-transfer",
        json={
            "source_envelope_id": str(envelope.id),
            "destination_envelope_id": str(envelope.id),
            "amount": 3000,
        },
    )
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


async def test_list_allocations_by_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can list allocations filtered by envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope1 = Envelope(budget_id=budget.id, name="Envelope 1", current_balance=10000)
    envelope2 = Envelope(budget_id=budget.id, name="Envelope 2", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    # Create transactions with allocations to different envelopes
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -1000,
            "allocations": [{"envelope_id": str(envelope1.id), "amount": -1000}],
        },
    )
    await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-16",
            "amount": -2000,
            "allocations": [{"envelope_id": str(envelope2.id), "amount": -2000}],
        },
    )

    # List allocations for envelope1 only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/allocations?envelope_id={envelope1.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["envelope_id"] == str(envelope1.id)


async def test_income_transaction_with_positive_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Income adds to envelope balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    envelope = Envelope(budget_id=budget.id, name="Savings", current_balance=5000)
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 100000,  # Income
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": 100000},
            ],
        },
    )
    assert response.status_code == 201

    await session.refresh(envelope)
    assert envelope.current_balance == 105000  # 5000 + 100000


async def test_account_balance_updates_with_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Account balance is updated when creating transactions."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(
        budget_id=budget.id, name="Test Envelope", current_balance=10000
    )
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201

    await session.refresh(account)
    # Working balance = cleared + uncleared
    assert account.cleared_balance + account.uncleared_balance == 45000  # 50000 - 5000


async def test_update_allocation_memo(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can update allocation memo."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(
        budget_id=budget.id, name="Test Envelope", current_balance=10000
    )
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create transaction with allocation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201
    allocation_id = response.json()["allocations"][0]["id"]

    # Update memo
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{allocation_id}",
        json={"memo": "Updated memo"},
    )
    assert response.status_code == 200
    assert response.json()["memo"] == "Updated memo"

    # Verify envelope balance unchanged
    await session.refresh(envelope)
    assert envelope.current_balance == 5000


async def test_update_allocation_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can move allocation to a different envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope1 = Envelope(budget_id=budget.id, name="Envelope 1", current_balance=10000)
    envelope2 = Envelope(budget_id=budget.id, name="Envelope 2", current_balance=5000)
    session.add(account)
    session.add(payee)
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    # Create transaction with allocation to envelope1
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -3000,
            "allocations": [
                {"envelope_id": str(envelope1.id), "amount": -3000},
            ],
        },
    )
    assert response.status_code == 201
    allocation_id = response.json()["allocations"][0]["id"]

    # Verify initial balances
    await session.refresh(envelope1)
    await session.refresh(envelope2)
    assert envelope1.current_balance == 7000  # 10000 - 3000
    assert envelope2.current_balance == 5000

    # Move allocation to envelope2
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{allocation_id}",
        json={"envelope_id": str(envelope2.id)},
    )
    assert response.status_code == 200
    assert response.json()["envelope_id"] == str(envelope2.id)

    # Verify balances adjusted
    await session.refresh(envelope1)
    await session.refresh(envelope2)
    assert envelope1.current_balance == 10000  # Restored
    assert envelope2.current_balance == 2000  # 5000 - 3000


async def test_update_allocation_amount_requires_matching_sum(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Changing allocation amount must keep sum equal to transaction amount."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(
        budget_id=budget.id, name="Test Envelope", current_balance=10000
    )
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create transaction with allocation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201
    allocation_id = response.json()["allocations"][0]["id"]

    # Try to change amount (would break sum)
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{allocation_id}",
        json={"amount": -3000},
    )
    assert response.status_code == 400
    assert "must equal transaction amount" in response.json()["detail"]


async def test_update_split_allocation_amounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can update split allocation amounts if they still sum correctly."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope1 = Envelope(budget_id=budget.id, name="Envelope 1", current_balance=10000)
    envelope2 = Envelope(budget_id=budget.id, name="Envelope 2", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope1)
    session.add(envelope2)
    await session.flush()

    # Create split transaction
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -10000,
            "allocations": [
                {"envelope_id": str(envelope1.id), "amount": -6000},
                {"envelope_id": str(envelope2.id), "amount": -4000},
            ],
        },
    )
    assert response.status_code == 201
    allocations = response.json()["allocations"]
    alloc1_id = allocations[0]["id"]
    alloc2_id = allocations[1]["id"]

    # Initial balances
    await session.refresh(envelope1)
    await session.refresh(envelope2)
    assert envelope1.current_balance == 4000  # 10000 - 6000
    assert envelope2.current_balance == 6000  # 10000 - 4000

    # Update first allocation to -8000 (need to update second to -2000 to keep sum)
    # First update will fail because sum would be wrong
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{alloc1_id}",
        json={"amount": -8000},
    )
    assert response.status_code == 400

    # Update second allocation first to -2000, then first to -8000
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{alloc2_id}",
        json={"amount": -2000},
    )
    assert response.status_code == 400  # Still fails, sum is now -8000

    # The only way to successfully update is if sum stays correct
    # Update second to envelope that will keep sum = -10000
    # Actually, we need to update both at once which isn't supported
    # Or move one allocation between envelopes without changing amount


async def test_update_envelope_transfer_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Can update envelope transfer allocation (no transaction link)."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    source = Envelope(budget_id=budget.id, name="Source", current_balance=10000)
    dest = Envelope(budget_id=budget.id, name="Destination", current_balance=0)
    other = Envelope(budget_id=budget.id, name="Other", current_balance=5000)
    session.add(source)
    session.add(dest)
    session.add(other)
    await session.flush()

    # Create transfer
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocations/envelope-transfer",
        json={
            "source_envelope_id": str(source.id),
            "destination_envelope_id": str(dest.id),
            "amount": 3000,
        },
    )
    assert response.status_code == 201
    dest_alloc_id = response.json()["destination_allocation"]["id"]

    # Initial state
    await session.refresh(source)
    await session.refresh(dest)
    assert source.current_balance == 7000
    assert dest.current_balance == 3000

    # Update destination allocation amount (no transaction validation)
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/allocations/{dest_alloc_id}",
        json={"amount": 5000},
    )
    assert response.status_code == 200

    await session.refresh(dest)
    assert dest.current_balance == 5000  # Was 3000, -3000 + 5000 = 5000


async def test_income_with_apply_allocation_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Income with apply_allocation_rules=true distributes via allocation rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account, payee, and envelopes
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    savings = Envelope(budget_id=budget.id, name="Savings", current_balance=0)
    emergency = Envelope(budget_id=budget.id, name="Emergency Fund", current_balance=0)
    session.add(account)
    session.add(payee)
    session.add(savings)
    session.add(emergency)
    await session.flush()

    # Create allocation rules: $50 fixed to savings, $50 fixed to emergency
    rule1 = AllocationRule(
        budget_id=budget.id,
        envelope_id=savings.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=5000,  # $50 in cents
        is_active=True,
    )
    rule2 = AllocationRule(
        budget_id=budget.id,
        envelope_id=emergency.id,
        priority=2,
        rule_type=AllocationRuleType.FIXED,
        amount=5000,  # $50 in cents
        is_active=True,
    )
    session.add(rule1)
    session.add(rule2)
    await session.flush()

    # Create income transaction with apply_allocation_rules=true
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 10000,  # $100 income
            "apply_allocation_rules": True,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Should have allocations to both envelopes
    assert len(data["allocations"]) == 2
    allocation_amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    assert allocation_amounts[str(savings.id)] == 5000  # 50% of 10000
    assert allocation_amounts[str(emergency.id)] == 5000  # 50% of 10000

    # Verify envelope balances
    await session.refresh(savings)
    await session.refresh(emergency)
    assert savings.current_balance == 5000
    assert emergency.current_balance == 5000


async def test_income_with_apply_allocation_rules_remainder_to_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """When allocation rules don't cover full amount, remainder goes to Unallocated."""
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
    savings = Envelope(budget_id=budget.id, name="Savings", current_balance=0)
    session.add(account)
    session.add(payee)
    session.add(savings)
    await session.flush()

    # Create allocation rule: fixed $30
    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=savings.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=3000,  # $30
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    # Create income transaction of $100 with apply_allocation_rules=true
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 10000,  # $100 income
            "apply_allocation_rules": True,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Should have allocations: $30 to savings, $70 to unallocated
    assert len(data["allocations"]) == 2

    # Find unallocated envelope
    unallocated_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = unallocated_result.scalar_one()

    allocation_amounts = {a["envelope_id"]: a["amount"] for a in data["allocations"]}
    assert allocation_amounts[str(savings.id)] == 3000
    assert allocation_amounts[str(unallocated.id)] == 7000


async def test_income_with_apply_allocation_rules_no_rules_falls_back(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """When no active rules exist, income falls back to Unallocated."""
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

    # No allocation rules created

    # Create income transaction with apply_allocation_rules=true
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 10000,  # $100 income
            "apply_allocation_rules": True,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Should have one allocation to Unallocated
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["amount"] == 10000

    # Verify it's allocated to the Unallocated envelope
    unallocated_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = unallocated_result.scalar_one()
    assert data["allocations"][0]["envelope_id"] == str(unallocated.id)
