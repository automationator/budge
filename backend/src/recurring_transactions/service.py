from datetime import date
from uuid import UUID, uuid7

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.service import get_account_by_id
from src.allocations.service import (
    create_allocation,
    reverse_allocations_for_transaction,
)
from src.envelopes.service import ensure_unallocated_envelope
from src.recurring_transactions.exceptions import RecurringTransactionNotFoundError
from src.recurring_transactions.models import RecurringTransaction
from src.recurring_transactions.recurrence import calculate_next_date
from src.recurring_transactions.schemas import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
)
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.transactions.service import update_account_balance


async def _create_transfer_allocation_if_needed(
    session: AsyncSession,
    budget_id: UUID,
    rule: RecurringTransaction,
    source_txn: Transaction,
) -> None:
    """Create an allocation for a budget-to-tracking transfer.

    When money leaves a budget account and goes to a tracking account,
    we need an allocation to record which envelope the money came from.
    """
    source_account = await get_account_by_id(session, budget_id, rule.account_id)
    if not source_account.include_in_budget:
        return

    dest_account = await get_account_by_id(
        session, budget_id, rule.destination_account_id
    )
    if dest_account.include_in_budget:
        return  # Budget-to-budget transfers don't need allocations

    envelope_id = rule.envelope_id
    if not envelope_id:
        unallocated = await ensure_unallocated_envelope(session, budget_id)
        envelope_id = unallocated.id

    await create_allocation(
        session=session,
        budget_id=budget_id,
        envelope_id=envelope_id,
        amount=source_txn.amount,
        date=source_txn.date,
        group_id=uuid7(),
        execution_order=0,
        transaction_id=source_txn.id,
    )


async def list_recurring_transactions(
    session: AsyncSession,
    budget_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[RecurringTransaction]:
    """List all recurring transactions for a budget."""
    query = select(RecurringTransaction).where(
        RecurringTransaction.budget_id == budget_id
    )

    if not include_inactive:
        query = query.where(RecurringTransaction.is_active == True)  # noqa: E712

    query = query.order_by(RecurringTransaction.next_occurrence_date.asc())

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_next_scheduled_dates(
    session: AsyncSession,
    recurring_ids: list[UUID],
) -> dict[UUID, date | None]:
    """Get the earliest scheduled transaction date for each recurring rule.

    Returns a dict mapping recurring_id to the next scheduled date (or None if no scheduled).
    """
    if not recurring_ids:
        return {}

    # Query the minimum scheduled date for each recurring transaction
    result = await session.execute(
        select(
            Transaction.recurring_transaction_id,
            func.min(Transaction.date).label("next_scheduled"),
        )
        .where(
            Transaction.recurring_transaction_id.in_(recurring_ids),
            Transaction.status == TransactionStatus.SCHEDULED,
        )
        .group_by(Transaction.recurring_transaction_id)
    )

    return {row[0]: row[1] for row in result.all()}


async def get_recurring_transaction_by_id(
    session: AsyncSession, budget_id: UUID, recurring_id: UUID
) -> RecurringTransaction:
    """Get a recurring transaction by ID."""
    result = await session.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.budget_id == budget_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise RecurringTransactionNotFoundError(recurring_id)
    return rule


async def create_recurring_transaction(
    session: AsyncSession, budget_id: UUID, data: RecurringTransactionCreate
) -> RecurringTransaction:
    """Create a new recurring transaction and generate initial occurrences."""
    rule = RecurringTransaction(
        budget_id=budget_id,
        account_id=data.account_id,
        destination_account_id=data.destination_account_id,
        payee_id=data.payee_id,
        location_id=data.location_id,
        user_id=data.user_id,
        envelope_id=data.envelope_id,
        frequency_value=data.frequency_value,
        frequency_unit=data.frequency_unit,
        start_date=data.start_date,
        end_date=data.end_date,
        amount=data.amount,
        memo=data.memo,
        next_occurrence_date=data.start_date,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    # Generate initial occurrences
    await generate_occurrences(session, rule)

    return rule


async def update_recurring_transaction(
    session: AsyncSession,
    budget_id: UUID,
    recurring_id: UUID,
    data: RecurringTransactionUpdate,
    *,
    propagate_to_future: bool = True,
) -> RecurringTransaction:
    """Update a recurring transaction.

    If propagate_to_future is True, updates unmodified scheduled transactions.
    """
    rule = await get_recurring_transaction_by_id(session, budget_id, recurring_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    if propagate_to_future:
        if rule.destination_account_id:
            # For transfers, update both linked transactions
            # Update source transactions (negative amount)
            await session.execute(
                update(Transaction)
                .where(
                    Transaction.recurring_transaction_id == recurring_id,
                    Transaction.status == TransactionStatus.SCHEDULED,
                    Transaction.is_modified == False,  # noqa: E712
                    Transaction.amount < 0,
                )
                .values(
                    amount=-abs(rule.amount),
                    account_id=rule.account_id,
                    location_id=rule.location_id,
                    memo=rule.memo,
                )
            )
            # Update destination transactions (positive amount)
            await session.execute(
                update(Transaction)
                .where(
                    Transaction.recurring_transaction_id == recurring_id,
                    Transaction.status == TransactionStatus.SCHEDULED,
                    Transaction.is_modified == False,  # noqa: E712
                    Transaction.amount > 0,
                )
                .values(
                    amount=abs(rule.amount),
                    account_id=rule.destination_account_id,
                    location_id=rule.location_id,
                    memo=rule.memo,
                )
            )
        else:
            # Regular transaction update
            await session.execute(
                update(Transaction)
                .where(
                    Transaction.recurring_transaction_id == recurring_id,
                    Transaction.status == TransactionStatus.SCHEDULED,
                    Transaction.is_modified == False,  # noqa: E712
                )
                .values(
                    amount=rule.amount,
                    payee_id=rule.payee_id,
                    account_id=rule.account_id,
                    location_id=rule.location_id,
                    memo=rule.memo,
                )
            )

    await session.flush()
    return rule


async def delete_recurring_transaction(
    session: AsyncSession,
    budget_id: UUID,
    recurring_id: UUID,
    *,
    delete_scheduled: bool = True,
) -> None:
    """Delete a recurring transaction.

    If delete_scheduled is True, also deletes future scheduled occurrences.
    Posted transactions are preserved (FK becomes NULL via SET NULL).
    """
    rule = await get_recurring_transaction_by_id(session, budget_id, recurring_id)

    if delete_scheduled:
        # Get and delete scheduled transactions
        result = await session.execute(
            select(Transaction).where(
                Transaction.recurring_transaction_id == recurring_id,
                Transaction.status == TransactionStatus.SCHEDULED,
            )
        )
        for txn in result.scalars().all():
            await reverse_allocations_for_transaction(session, budget_id, txn.id)
            await session.delete(txn)

    await session.delete(rule)
    await session.flush()


async def generate_occurrences(
    session: AsyncSession,
    rule: RecurringTransaction,
) -> list[Transaction]:
    """Generate the next scheduled transaction instance for a recurring rule.

    Generates exactly one occurrence at next_occurrence_date.
    """
    if not rule.is_active:
        return []

    today = date.today()
    occurrence_date = rule.next_occurrence_date

    # Don't generate if past end_date
    if rule.end_date and occurrence_date > rule.end_date:
        return []

    # Check if there's already a SCHEDULED transaction for this rule
    existing_result = await session.execute(
        select(Transaction.id)
        .where(
            Transaction.recurring_transaction_id == rule.id,
            Transaction.status == TransactionStatus.SCHEDULED,
        )
        .limit(1)
    )
    if existing_result.scalar_one_or_none():
        return []  # Already have a scheduled instance

    # Get next occurrence_index
    result = await session.execute(
        select(func.max(Transaction.occurrence_index)).where(
            Transaction.recurring_transaction_id == rule.id
        )
    )
    occurrence_index = (result.scalar() or 0) + 1

    # Determine status based on date
    status = (
        TransactionStatus.POSTED
        if occurrence_date <= today
        else TransactionStatus.SCHEDULED
    )

    transactions: list[Transaction] = []

    if rule.destination_account_id:
        # Create linked transfer pair
        source_txn = Transaction(
            budget_id=rule.budget_id,
            account_id=rule.account_id,
            payee_id=None,
            location_id=rule.location_id,
            user_id=rule.user_id,
            date=occurrence_date,
            amount=-abs(rule.amount),
            memo=rule.memo,
            status=status,
            transaction_type=TransactionType.TRANSFER,
            recurring_transaction_id=rule.id,
            occurrence_index=occurrence_index,
            is_modified=False,
            is_cleared=False,
        )
        dest_txn = Transaction(
            budget_id=rule.budget_id,
            account_id=rule.destination_account_id,
            payee_id=None,
            location_id=rule.location_id,
            user_id=rule.user_id,
            date=occurrence_date,
            amount=abs(rule.amount),
            memo=rule.memo,
            status=status,
            transaction_type=TransactionType.TRANSFER,
            recurring_transaction_id=rule.id,
            occurrence_index=occurrence_index,
            is_modified=False,
            is_cleared=False,
        )
        session.add(source_txn)
        session.add(dest_txn)
        await session.flush()  # Insert rows before setting FK references
        # Link them bidirectionally
        source_txn.linked_transaction_id = dest_txn.id
        dest_txn.linked_transaction_id = source_txn.id
        transactions.extend([source_txn, dest_txn])

        # Create allocation for POSTED budget-to-tracking transfers
        if status == TransactionStatus.POSTED:
            await _create_transfer_allocation_if_needed(
                session, rule.budget_id, rule, source_txn
            )
    else:
        # Regular transaction
        txn = Transaction(
            budget_id=rule.budget_id,
            account_id=rule.account_id,
            payee_id=rule.payee_id,
            location_id=rule.location_id,
            user_id=rule.user_id,
            date=occurrence_date,
            amount=rule.amount,
            memo=rule.memo,
            status=status,
            recurring_transaction_id=rule.id,
            occurrence_index=occurrence_index,
            is_modified=False,
            is_cleared=False,
        )
        session.add(txn)
        transactions.append(txn)

        # Create allocation for POSTED transactions (for budget accounts)
        if status == TransactionStatus.POSTED:
            account = await get_account_by_id(session, rule.budget_id, rule.account_id)
            if account.include_in_budget:
                await (
                    session.flush()
                )  # Ensure transaction exists in DB for FK constraint
                # Use specified envelope or default to Unallocated
                envelope_id = rule.envelope_id
                if not envelope_id:
                    unallocated = await ensure_unallocated_envelope(
                        session, rule.budget_id
                    )
                    envelope_id = unallocated.id
                await create_allocation(
                    session=session,
                    budget_id=rule.budget_id,
                    envelope_id=envelope_id,
                    amount=txn.amount,
                    date=txn.date,
                    group_id=uuid7(),
                    execution_order=0,
                    transaction_id=txn.id,
                )

    # Update next_occurrence_date to the following occurrence
    rule.next_occurrence_date = calculate_next_date(
        occurrence_date,
        rule.frequency_value,
        rule.frequency_unit,
    )

    await session.flush()
    return transactions


async def realize_due_transactions(
    session: AsyncSession,
    budget_id: UUID,
) -> int:
    """Move SCHEDULED transactions to POSTED when date <= today.

    Creates allocations for transactions linked to recurring rules with envelope_id.
    Returns the count of realized transactions.
    """
    today = date.today()

    # Get transactions to realize (need full objects for allocation creation).
    # SKIP LOCKED as defense-in-depth: if a concurrent session bypasses the
    # advisory lock in process_recurring(), locked rows are skipped instead
    # of double-processed.
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.SCHEDULED,
            Transaction.date <= today,
        )
        .with_for_update(skip_locked=True)
    )
    transactions = list(result.scalars().all())

    if not transactions:
        return 0

    # Get unique recurring_transaction_ids
    recurring_ids = {
        t.recurring_transaction_id for t in transactions if t.recurring_transaction_id
    }

    # Load recurring transactions for envelope allocation
    rules_by_id: dict[UUID, RecurringTransaction] = {}
    if recurring_ids:
        rules_result = await session.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.id.in_(recurring_ids),
            )
        )
        rules_by_id = {r.id: r for r in rules_result.scalars().all()}

    # Process each transaction
    for txn in transactions:
        txn.status = TransactionStatus.POSTED

        # Update account balance now that transaction is posted
        account = await get_account_by_id(session, budget_id, txn.account_id)
        update_account_balance(account, txn.amount, txn.is_cleared)

        # Create allocations for recurring transactions on budget accounts
        if txn.recurring_transaction_id and txn.recurring_transaction_id in rules_by_id:
            rule = rules_by_id[txn.recurring_transaction_id]

            if txn.transaction_type == TransactionType.TRANSFER:
                # For transfers, only create allocation on the source side
                if txn.amount < 0:
                    await _create_transfer_allocation_if_needed(
                        session, budget_id, rule, txn
                    )
            else:
                # Non-transfer: existing logic
                account = await get_account_by_id(session, budget_id, rule.account_id)
                if account.include_in_budget:
                    envelope_id = rule.envelope_id
                    if not envelope_id:
                        unallocated = await ensure_unallocated_envelope(
                            session, budget_id
                        )
                        envelope_id = unallocated.id
                    await create_allocation(
                        session=session,
                        budget_id=budget_id,
                        envelope_id=envelope_id,
                        amount=txn.amount,
                        date=txn.date,
                        group_id=uuid7(),
                        execution_order=0,
                        transaction_id=txn.id,
                    )

    await session.flush()
    return len(transactions)


async def ensure_next_occurrence(
    session: AsyncSession,
    budget_id: UUID,
) -> None:
    """Ensure all active recurring rules have a scheduled occurrence.

    Generates the next occurrence if no SCHEDULED transaction exists.
    """
    # Get active rules that have no SCHEDULED transactions
    result = await session.execute(
        select(RecurringTransaction)
        .where(
            RecurringTransaction.budget_id == budget_id,
            RecurringTransaction.is_active == True,  # noqa: E712
        )
        .where(
            ~RecurringTransaction.id.in_(
                select(Transaction.recurring_transaction_id).where(
                    Transaction.budget_id == budget_id,
                    Transaction.status == TransactionStatus.SCHEDULED,
                    Transaction.recurring_transaction_id.isnot(None),
                )
            )
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        await generate_occurrences(session, rule)


async def process_recurring(session: AsyncSession, budget_id: UUID) -> int:
    """Process recurring transactions on app access.

    Realizes due transactions and ensures next occurrences are generated.
    Uses a PostgreSQL advisory lock to prevent concurrent processing from
    duplicate requests (e.g., multiple frontend calls on page load).
    Returns the count of realized transactions.
    """
    lock_id = int.from_bytes(budget_id.bytes[:8], "big") & 0x7FFFFFFFFFFFFFFF
    result = await session.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
        {"lock_id": lock_id},
    )
    if not result.scalar():
        return 0  # Another request is already processing

    realized_count = await realize_due_transactions(session, budget_id)
    await ensure_next_occurrence(session, budget_id)
    return realized_count
