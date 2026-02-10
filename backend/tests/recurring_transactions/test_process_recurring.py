from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.recurring_transactions.recurrence import calculate_next_date
from src.recurring_transactions.service import process_recurring
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User


async def test_process_recurring_idempotent(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Calling process_recurring twice produces only 1 allocation and 1 next occurrence.

    Simulates the scenario where a SCHEDULED transaction is due today and
    process_recurring is called multiple times (e.g., from concurrent page loads).
    Within a single session the advisory lock is re-entrant, so this test
    validates the logical idempotency: realize_due_transactions finds nothing
    on the second call, and ensure_next_occurrence doesn't duplicate.
    """
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Idempotency Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    payee = Payee(budget_id=budget.id, name="Idempotency Mortgage")
    envelope = Envelope(
        budget_id=budget.id,
        name="Idempotency Mortgage Envelope",
        current_balance=0,
    )
    session.add_all([account, payee, envelope])
    await session.flush()

    # Simulate state as if generate_occurrences already ran: the rule's
    # next_occurrence_date is advanced to next month, and a SCHEDULED
    # transaction exists for today (it was created when today was still
    # in the future).
    next_date = calculate_next_date(date.today(), 1, FrequencyUnit.MONTHS)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        envelope_id=envelope.id,
        amount=-183172,  # -$1,831.72
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=next_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=-183172,
        status=TransactionStatus.SCHEDULED,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    session.add(scheduled_txn)
    await session.flush()

    # First call: should realize the due transaction and create next occurrence
    count1 = await process_recurring(session, budget.id)
    await session.flush()

    # Second call: should be a no-op
    count2 = await process_recurring(session, budget.id)
    await session.flush()

    # First call realized 1 transaction
    assert count1 == 1

    # Second call found nothing to do
    assert count2 == 0

    # Exactly 1 allocation was created
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.envelope_id == envelope.id,
        )
    )
    allocations = list(alloc_result.scalars().all())
    assert len(allocations) == 1
    assert allocations[0].amount == -183172

    # Envelope balance updated exactly once
    await session.refresh(envelope)
    assert envelope.current_balance == -183172

    # Exactly 1 SCHEDULED transaction for next month
    scheduled_result = await session.execute(
        select(Transaction).where(
            Transaction.recurring_transaction_id == rule.id,
            Transaction.status == TransactionStatus.SCHEDULED,
        )
    )
    scheduled = list(scheduled_result.scalars().all())
    assert len(scheduled) == 1
    assert scheduled[0].date > date.today()
    assert scheduled[0].date <= date.today() + timedelta(days=31)

    # The original transaction is now POSTED
    await session.refresh(scheduled_txn)
    assert scheduled_txn.status == TransactionStatus.POSTED


async def test_realize_transfer_budget_to_tracking_creates_allocation(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Realizing a budget-to-tracking transfer creates an allocation on the source side."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    budget_account = Account(
        budget_id=budget.id,
        name="Budget Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    envelope = Envelope(
        budget_id=budget.id,
        name="Investment Envelope",
        current_balance=0,
    )
    session.add_all([budget_account, tracking_account, envelope])
    await session.flush()

    next_date = calculate_next_date(date.today(), 1, FrequencyUnit.MONTHS)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        destination_account_id=tracking_account.id,
        envelope_id=envelope.id,
        amount=200000,  # $2,000
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=next_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    # Create linked transfer pair as SCHEDULED (as generate_occurrences would)
    source_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        date=date.today(),
        amount=-200000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    dest_txn = Transaction(
        budget_id=budget.id,
        account_id=tracking_account.id,
        date=date.today(),
        amount=200000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    session.add_all([source_txn, dest_txn])
    await session.flush()
    source_txn.linked_transaction_id = dest_txn.id
    dest_txn.linked_transaction_id = source_txn.id
    await session.flush()

    count = await process_recurring(session, budget.id)
    await session.flush()

    # Both source and dest transactions realized
    assert count == 2

    # Allocation created on the source (budget account) side
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id == source_txn.id,
        )
    )
    allocations = list(alloc_result.scalars().all())
    assert len(allocations) == 1
    assert allocations[0].amount == -200000
    assert allocations[0].envelope_id == envelope.id

    # No allocation on the dest (tracking account) side
    dest_alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id == dest_txn.id,
        )
    )
    assert dest_alloc_result.scalar_one_or_none() is None

    # Envelope balance updated
    await session.refresh(envelope)
    assert envelope.current_balance == -200000


async def test_realize_transfer_budget_to_tracking_no_envelope_uses_unallocated(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Budget-to-tracking transfer with no envelope_id falls back to Unallocated."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    budget_account = Account(
        budget_id=budget.id,
        name="Budget Checking Unalloc",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Investment Unalloc",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    session.add_all([budget_account, tracking_account])
    await session.flush()

    next_date = calculate_next_date(date.today(), 1, FrequencyUnit.MONTHS)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        destination_account_id=tracking_account.id,
        envelope_id=None,  # No envelope specified
        amount=100000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=next_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    source_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        date=date.today(),
        amount=-100000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    dest_txn = Transaction(
        budget_id=budget.id,
        account_id=tracking_account.id,
        date=date.today(),
        amount=100000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    session.add_all([source_txn, dest_txn])
    await session.flush()
    source_txn.linked_transaction_id = dest_txn.id
    dest_txn.linked_transaction_id = source_txn.id
    await session.flush()

    count = await process_recurring(session, budget.id)
    await session.flush()

    assert count == 2

    # Allocation created with the Unallocated envelope
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id == source_txn.id,
        )
    )
    allocations = list(alloc_result.scalars().all())
    assert len(allocations) == 1
    assert allocations[0].amount == -100000

    # Verify it used the Unallocated envelope
    unalloc_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated_envelope = unalloc_result.scalar_one()
    assert allocations[0].envelope_id == unallocated_envelope.id


async def test_realize_transfer_budget_to_budget_no_allocation(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Budget-to-budget transfers should NOT create allocations."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="B2B Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    savings = Account(
        budget_id=budget.id,
        name="B2B Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    session.add_all([checking, savings])
    await session.flush()

    next_date = calculate_next_date(date.today(), 1, FrequencyUnit.MONTHS)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=checking.id,
        destination_account_id=savings.id,
        amount=50000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today(),
        next_occurrence_date=next_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    source_txn = Transaction(
        budget_id=budget.id,
        account_id=checking.id,
        date=date.today(),
        amount=-50000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    dest_txn = Transaction(
        budget_id=budget.id,
        account_id=savings.id,
        date=date.today(),
        amount=50000,
        status=TransactionStatus.SCHEDULED,
        transaction_type=TransactionType.TRANSFER,
        recurring_transaction_id=rule.id,
        occurrence_index=1,
        is_modified=False,
        is_cleared=False,
    )
    session.add_all([source_txn, dest_txn])
    await session.flush()
    source_txn.linked_transaction_id = dest_txn.id
    dest_txn.linked_transaction_id = source_txn.id
    await session.flush()

    count = await process_recurring(session, budget.id)
    await session.flush()

    assert count == 2

    # No allocations created for budget-to-budget transfer
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id.in_([source_txn.id, dest_txn.id]),
        )
    )
    assert list(alloc_result.scalars().all()) == []


async def test_generate_transfer_budget_to_tracking_posted(
    session: AsyncSession,
    test_user: User,
) -> None:
    """generate_occurrences for a past-due transfer creates POSTED txns with allocation."""
    from src.recurring_transactions.service import generate_occurrences

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    budget_account = Account(
        budget_id=budget.id,
        name="Gen Posted Budget",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Gen Posted Tracking",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    envelope = Envelope(
        budget_id=budget.id,
        name="Gen Posted Envelope",
        current_balance=0,
    )
    session.add_all([budget_account, tracking_account, envelope])
    await session.flush()

    # Rule with next_occurrence_date in the past (yesterday)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        destination_account_id=tracking_account.id,
        envelope_id=envelope.id,
        amount=150000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=date.today() - timedelta(days=1),
        next_occurrence_date=date.today() - timedelta(days=1),
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    transactions = await generate_occurrences(session, rule)
    await session.flush()

    # Should create 2 transactions (source + dest), both POSTED
    assert len(transactions) == 2
    source_txn = next(t for t in transactions if t.amount < 0)
    dest_txn = next(t for t in transactions if t.amount > 0)
    assert source_txn.status == TransactionStatus.POSTED
    assert dest_txn.status == TransactionStatus.POSTED

    # Allocation created on source transaction
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id == source_txn.id,
        )
    )
    allocations = list(alloc_result.scalars().all())
    assert len(allocations) == 1
    assert allocations[0].amount == -150000
    assert allocations[0].envelope_id == envelope.id

    # Envelope balance updated
    await session.refresh(envelope)
    assert envelope.current_balance == -150000


async def test_generate_transfer_budget_to_tracking_scheduled(
    session: AsyncSession,
    test_user: User,
) -> None:
    """generate_occurrences for a future transfer creates SCHEDULED txns without allocation."""
    from src.recurring_transactions.service import generate_occurrences

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    budget_account = Account(
        budget_id=budget.id,
        name="Gen Sched Budget",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=0,
        uncleared_balance=0,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Gen Sched Tracking",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    envelope = Envelope(
        budget_id=budget.id,
        name="Gen Sched Envelope",
        current_balance=0,
    )
    session.add_all([budget_account, tracking_account, envelope])
    await session.flush()

    # Rule with next_occurrence_date in the future
    future_date = date.today() + timedelta(days=7)
    rule = RecurringTransaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        destination_account_id=tracking_account.id,
        envelope_id=envelope.id,
        amount=150000,
        frequency_value=1,
        frequency_unit=FrequencyUnit.MONTHS,
        start_date=future_date,
        next_occurrence_date=future_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    transactions = await generate_occurrences(session, rule)
    await session.flush()

    # Should create 2 SCHEDULED transactions
    assert len(transactions) == 2
    source_txn = next(t for t in transactions if t.amount < 0)
    dest_txn = next(t for t in transactions if t.amount > 0)
    assert source_txn.status == TransactionStatus.SCHEDULED
    assert dest_txn.status == TransactionStatus.SCHEDULED

    # No allocations created for scheduled transactions
    alloc_result = await session.execute(
        select(Allocation).where(
            Allocation.budget_id == budget.id,
            Allocation.transaction_id.in_([source_txn.id, dest_txn.id]),
        )
    )
    assert list(alloc_result.scalars().all()) == []

    # Envelope balance unchanged
    await session.refresh(envelope)
    assert envelope.current_balance == 0
