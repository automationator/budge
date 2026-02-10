from datetime import date
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.envelopes.service import (
    calculate_unallocated_balance,
    create_cc_envelope,
    ensure_unallocated_envelope,
    recalculate_envelope_balances,
)
from src.payees.models import Payee
from src.transactions.models import Transaction
from src.users.models import User


async def test_delete_transfer_reverses_budget_to_tracking_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a budget-to-tracking transfer restores envelope balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget and tracking accounts
    budget_account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    session.add(budget_account)
    session.add(tracking_account)
    await session.flush()

    # Create envelope with initial balance
    envelope = Envelope(budget_id=budget.id, name="Investments", current_balance=20000)
    session.add(envelope)
    await session.flush()

    # Create budget-to-tracking transfer with envelope
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(budget_account.id),
            "destination_account_id": str(tracking_account.id),
            "date": "2024-01-15",
            "amount": 10000,
            "envelope_id": str(envelope.id),
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_txn_id = data["source_transaction"]["id"]

    # Verify envelope balance was reduced by the transfer
    await session.refresh(envelope)
    assert envelope.current_balance == 10000  # 20000 - 10000

    # Delete the transfer
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_txn_id}",
    )
    assert response.status_code == 204

    # Verify envelope balance was restored
    await session.refresh(envelope)
    assert envelope.current_balance == 20000  # Restored to original


async def test_delete_transfer_reverses_cc_payment_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a CC payment transfer restores CC envelope balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create checking and CC accounts
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    cc_account = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=True,
        cleared_balance=-30000,  # $300 debt
    )
    session.add(checking)
    session.add(cc_account)
    await session.flush()

    # Create CC envelope (linked to CC account) with balance representing pending payments
    cc_envelope = await create_cc_envelope(session, budget.id, cc_account)
    cc_envelope.current_balance = 20000  # $200 set aside for payment
    await session.flush()

    # Create CC payment transfer (checking -> CC)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(cc_account.id),
            "date": "2024-01-15",
            "amount": 15000,  # $150 payment
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_txn_id = data["source_transaction"]["id"]

    # Verify CC envelope balance was reduced by the payment
    await session.refresh(cc_envelope)
    assert cc_envelope.current_balance == 5000  # 20000 - 15000

    # Delete the transfer
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_txn_id}",
    )
    assert response.status_code == 204

    # Verify CC envelope balance was restored
    await session.refresh(cc_envelope)
    assert cc_envelope.current_balance == 20000  # Restored to original


async def test_delete_transfer_reverses_account_balances(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a transfer restores both account balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    savings = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=True,
        cleared_balance=30000,
    )
    session.add(checking)
    session.add(savings)
    await session.flush()

    # Create transfer: checking -> savings for $100
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(savings.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_txn_id = data["source_transaction"]["id"]

    # Verify balances changed
    await session.refresh(checking)
    await session.refresh(savings)
    assert checking.uncleared_balance == -10000  # Money left
    assert savings.uncleared_balance == 10000  # Money arrived

    # Delete the transfer
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_txn_id}",
    )
    assert response.status_code == 204

    # Verify account balances restored
    await session.refresh(checking)
    await session.refresh(savings)
    assert checking.uncleared_balance == 0
    assert savings.uncleared_balance == 0
    assert checking.cleared_balance == 50000
    assert savings.cleared_balance == 30000


async def test_recalculate_envelope_balances(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate endpoint fixes drifted envelope balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create envelope with a wrong balance (simulating drift)
    envelope = Envelope(
        budget_id=budget.id,
        name="Groceries",
        current_balance=99999,  # Incorrect - no allocations exist
    )
    session.add(envelope)
    await session.flush()

    # Call recalculate endpoint
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes/recalculate-balances",
    )
    assert response.status_code == 200
    corrections = response.json()

    # Verify correction was returned
    assert len(corrections) == 1
    assert corrections[0]["envelope_id"] == str(envelope.id)
    assert corrections[0]["envelope_name"] == "Groceries"
    assert corrections[0]["old_balance"] == 99999
    assert corrections[0]["new_balance"] == 0

    # Verify envelope balance was actually fixed
    await session.refresh(envelope)
    assert envelope.current_balance == 0


async def test_recalculate_envelope_balances_no_corrections(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate endpoint returns empty when balances are correct."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create envelope with correct balance (0, no allocations)
    envelope = Envelope(
        budget_id=budget.id,
        name="Groceries",
        current_balance=0,
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes/recalculate-balances",
    )
    assert response.status_code == 200
    corrections = response.json()
    assert len(corrections) == 0


async def test_cc_payment_allocation_linked_to_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """CC payment allocations are linked to the destination transaction."""
    from src.allocations.models import Allocation

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    cc_account = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=True,
        cleared_balance=-20000,
    )
    session.add(checking)
    session.add(cc_account)
    await session.flush()

    cc_envelope = await create_cc_envelope(session, budget.id, cc_account)
    cc_envelope.current_balance = 15000
    await session.flush()

    # Create CC payment transfer
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(cc_account.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    dest_txn_id = data["destination_transaction"]["id"]

    # Verify the CC payment allocation is linked to the dest transaction
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == cc_envelope.id,
            Allocation.transaction_id == dest_txn_id,
        )
    )
    allocation = alloc_result.scalar_one_or_none()
    assert allocation is not None
    assert allocation.amount == -10000  # Negative (reducing CC envelope)
    assert allocation.transaction_id is not None  # Linked to transaction


async def test_recalculate_deletes_orphaned_allocations(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate deletes allocations referencing nonexistent transactions."""
    from sqlalchemy import text

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()
    budget_id = budget.id

    # Create an account and a real transaction so we can insert an allocation
    account = Account(
        budget_id=budget_id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    session.add(account)
    await session.flush()

    envelope = Envelope(budget_id=budget_id, name="Groceries", current_balance=5000)
    session.add(envelope)
    await session.flush()

    txn = Transaction(
        budget_id=budget_id,
        account_id=account.id,
        amount=5000,
        date=date(2024, 1, 15),
    )
    session.add(txn)
    await session.flush()

    # Create an allocation linked to the transaction
    alloc = Allocation(
        budget_id=budget_id,
        envelope_id=envelope.id,
        transaction_id=txn.id,
        group_id=uuid4(),
        amount=5000,
        date=date(2024, 1, 15),
    )
    session.add(alloc)
    await session.flush()
    alloc_id = alloc.id
    txn_id = txn.id

    # Orphan the allocation by deleting the transaction without cascade.
    # Temporarily disable FK triggers to bypass CASCADE deletion.
    await session.execute(text("SET session_replication_role = 'replica'"))
    await session.execute(
        text("DELETE FROM transactions WHERE id = :txn_id"),
        {"txn_id": txn_id},
    )
    await session.execute(text("SET session_replication_role = 'origin'"))
    # Expire the ORM cache so it re-reads from DB
    session.expire_all()

    # Recalculate should delete the orphaned allocation and fix the balance
    corrections = await recalculate_envelope_balances(session, budget_id)

    assert len(corrections) == 1
    assert corrections[0]["envelope_name"] == "Groceries"
    assert corrections[0]["old_balance"] == 5000
    assert corrections[0]["new_balance"] == 0

    # Verify the orphaned allocation was deleted
    alloc_result = await session.execute(
        select(Allocation).where(Allocation.id == alloc_id)
    )
    assert alloc_result.scalar_one_or_none() is None


async def test_recalculate_preserves_null_transaction_allocations(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate preserves allocations with transaction_id=None (transfers, CC payments)."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with enough balance so RTA stays non-negative
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=5000,
    )
    session.add(account)
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add(envelope)
    await session.flush()

    # Create a legitimate envelope transfer allocation (transaction_id=None)
    transfer_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=None,
        group_id=uuid4(),
        amount=3000,
        date=date(2024, 1, 15),
        memo="Envelope transfer",
    )
    # Create a legitimate CC payment allocation (transaction_id=None)
    cc_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=None,
        group_id=uuid4(),
        amount=-1000,
        date=date(2024, 1, 15),
        memo="Credit card payment",
    )
    session.add(transfer_alloc)
    session.add(cc_alloc)
    await session.flush()

    # Recalculate should preserve both allocations and set balance to their sum
    corrections = await recalculate_envelope_balances(session, budget.id)

    assert len(corrections) == 1
    assert corrections[0]["envelope_name"] == "Groceries"
    assert corrections[0]["old_balance"] == 0
    assert corrections[0]["new_balance"] == 2000  # 3000 + (-1000)

    # Verify both allocations still exist
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == envelope.id,
        )
    )
    allocs = list(alloc_result.scalars().all())
    assert len(allocs) == 2


async def test_recalculate_recreates_missing_cc_payment_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate recreates deleted CC payment allocations and fixes balances."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create checking and CC accounts
    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=100000,
    )
    cc_account = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=True,
        cleared_balance=-50000,
    )
    session.add(checking)
    session.add(cc_account)
    await session.flush()

    # Create CC envelope linked to CC account with allocations backing its balance
    cc_envelope = await create_cc_envelope(session, budget.id, cc_account)
    # Add backing allocation for $300 CC envelope balance (simulating CC spending)
    backing_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=cc_envelope.id,
        transaction_id=None,
        group_id=uuid4(),
        amount=30000,
        date=date(2024, 1, 10),
        memo="CC spending",
    )
    session.add(backing_alloc)
    cc_envelope.current_balance = 30000
    await session.flush()

    # Create a CC payment transfer (checking -> CC)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(cc_account.id),
            "date": "2024-01-15",
            "amount": 20000,  # $200 payment
        },
    )
    assert response.status_code == 201
    data = response.json()
    dest_txn_id = data["destination_transaction"]["id"]

    # Verify CC envelope was reduced by payment
    await session.refresh(cc_envelope)
    assert cc_envelope.current_balance == 10000  # 30000 - 20000

    # Verify the CC payment allocation exists
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == cc_envelope.id,
            Allocation.transaction_id == dest_txn_id,
        )
    )
    original_alloc = alloc_result.scalar_one()
    assert original_alloc.amount == -20000

    # Simulate the bad production fix: delete the CC payment allocation directly
    await session.delete(original_alloc)
    await session.flush()

    # Manually inflate the envelope balance to simulate the drift
    cc_envelope.current_balance = 30000  # Back to pre-payment balance (wrong)
    await session.flush()

    # Now run recalculate — it should recreate the missing allocation and fix balance
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes/recalculate-balances",
    )
    assert response.status_code == 200
    corrections = response.json()

    # Should have corrected CC envelope balance
    cc_corrections = [c for c in corrections if c["envelope_id"] == str(cc_envelope.id)]
    assert len(cc_corrections) == 1
    assert cc_corrections[0]["old_balance"] == 30000
    assert cc_corrections[0]["new_balance"] == 10000  # 30000 allocation - 20000 payment

    # Verify the allocation was recreated
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == cc_envelope.id,
            Allocation.transaction_id == dest_txn_id,
        )
    )
    recreated_alloc = alloc_result.scalar_one()
    assert recreated_alloc.amount == -20000
    assert recreated_alloc.memo == "Credit card payment"

    # Verify envelope balance is correct
    await session.refresh(cc_envelope)
    assert cc_envelope.current_balance == 10000


async def test_delete_income_after_distribution_from_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting income after distributing from Unallocated keeps RTA at 0."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
    )
    session.add(account)
    await session.flush()

    # Create payee, unallocated and regular envelopes
    payee = Payee(budget_id=budget.id, name="Employer")
    session.add(payee)
    unallocated = await ensure_unallocated_envelope(session, budget.id)
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add(envelope)
    await session.flush()

    # Create income transaction → goes to Unallocated
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 50000,
            "is_cleared": True,
            "apply_allocation_rules": False,
        },
    )
    assert response.status_code == 201
    income_txn_id = response.json()["id"]

    # Verify RTA = $500 (account has $500, no envelope allocations on regular envelopes)
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 50000

    # Distribute from Unallocated to Groceries (simulating "Auto Assign" / manual budgeting)
    # This creates a one-sided allocation: positive on Groceries, nothing on Unallocated
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/allocations/envelope-transfer",
        json={
            "source_envelope_id": str(unallocated.id),
            "destination_envelope_id": str(envelope.id),
            "amount": 50000,
        },
    )
    assert response.status_code == 201

    # Verify: RTA = 0, Groceries = $500
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 0
    await session.refresh(envelope)
    assert envelope.current_balance == 50000

    # Delete the income transaction
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{income_txn_id}",
    )
    assert response.status_code == 204

    # RTA should be 0, NOT -$500
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 0

    # The one-sided allocation should have been clawed back
    await session.refresh(envelope)
    assert envelope.current_balance == 0

    # Verify the one-sided allocation was deleted
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == envelope.id,
            Allocation.transaction_id.is_(None),
        )
    )
    assert alloc_result.scalar_one_or_none() is None


async def test_delete_income_with_inline_rules_no_clawback(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting income with transaction-linked allocations doesn't trigger clawback."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
    )
    session.add(account)
    await session.flush()

    # Create payee and envelopes
    payee = Payee(budget_id=budget.id, name="Employer")
    session.add(payee)
    await ensure_unallocated_envelope(session, budget.id)
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add(envelope)
    await session.flush()

    # Create income with explicit allocation to envelope (transaction-linked)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 50000,
            "is_cleared": True,
            "allocations": [
                {"envelope_id": str(envelope.id), "amount": 50000},
            ],
        },
    )
    assert response.status_code == 201
    income_txn_id = response.json()["id"]

    # Verify: RTA = 0 (account +$500, Groceries +$500)
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 0
    await session.refresh(envelope)
    assert envelope.current_balance == 50000

    # Delete the income
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{income_txn_id}",
    )
    assert response.status_code == 204

    # RTA should be 0 (account back to 0, envelope back to 0)
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 0
    await session.refresh(envelope)
    assert envelope.current_balance == 0


async def test_recalculate_fixes_negative_rta_from_orphaned_transfers(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Recalculate fixes negative RTA from orphaned one-sided transfers."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account with $0 balance (simulating deleted income)
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
    )
    session.add(account)
    await session.flush()

    # Create envelopes
    await ensure_unallocated_envelope(session, budget.id)
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=30000)
    session.add(envelope)
    await session.flush()

    # Manually create orphaned one-sided transfer allocation (simulating the bug)
    # This allocation has no matching negative sibling — it's from Unallocated
    orphaned_alloc = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=None,
        group_id=uuid4(),
        amount=30000,
        date=date(2024, 1, 15),
    )
    session.add(orphaned_alloc)
    await session.flush()

    # Verify RTA is negative (accounts=0, envelopes=30000 → RTA=-30000)
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == -30000

    # Run recalculate — should fix the negative RTA
    corrections = await recalculate_envelope_balances(session, budget.id)

    # Should have corrections for the RTA fix
    rta_corrections = [
        c for c in corrections if c["envelope_name"] == "Unallocated (Ready to Assign)"
    ]
    assert len(rta_corrections) == 1
    assert rta_corrections[0]["old_balance"] == -30000
    assert rta_corrections[0]["new_balance"] == 0

    # RTA should now be 0
    rta = await calculate_unallocated_balance(session, budget.id)
    assert rta == 0

    # The orphaned one-sided allocation should have been removed
    alloc_result = await session.execute(
        select(Allocation).where(Allocation.id == orphaned_alloc.id)
    )
    assert alloc_result.scalar_one_or_none() is None

    # Envelope balance should have been corrected
    await session.refresh(envelope)
    assert envelope.current_balance == 0
