from datetime import date as DateType
from uuid import UUID, uuid7

from sqlalchemy import distinct, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import Account, AccountType
from src.accounts.service import get_account_by_id
from src.allocation_rules.service import apply_rules_to_income
from src.allocations.exceptions import (
    AllocationAmountMismatchError,
)
from src.allocations.models import Allocation
from src.allocations.schemas import AllocationInput
from src.allocations.service import (
    create_allocations_for_transaction,
    delete_allocations_for_transaction,
    reverse_allocations_for_transaction,
)
from src.envelopes.service import (
    calculate_unallocated_balance,
    ensure_unallocated_envelope,
    get_cc_envelope_by_account_id,
    get_unallocated_envelope,
)
from src.exceptions import BadRequestError
from src.payees import service as payees_service
from src.recurring_transactions.models import RecurringTransaction
from src.transactions.exceptions import TransactionNotFoundError
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.transactions.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransferCreate,
    TransferUpdate,
)


def update_account_balance(account: Account, amount: int, is_cleared: bool) -> None:
    """Update the appropriate balance field based on cleared status.

    Args:
        account: The account to update
        amount: The amount to add (negative for subtracting)
        is_cleared: Whether the transaction is cleared
    """
    if is_cleared:
        account.cleared_balance += amount
    else:
        account.uncleared_balance += amount


async def list_transactions(
    session: AsyncSession,
    budget_id: UUID,
    *,
    limit: int = 50,
    cursor_date: DateType | None = None,
    cursor_id: UUID | None = None,
    account_id: UUID | None = None,
    envelope_id: UUID | None = None,
    status: list[TransactionStatus] | None = None,
    include_scheduled: bool = True,
    include_skipped: bool = False,
    is_reconciled: bool | None = None,
    include_in_budget: bool | None = None,
    payee_id: UUID | None = None,
    location_id: UUID | None = None,
    expenses_only: bool = False,
    exclude_adjustments: bool = False,
) -> tuple[list[Transaction], bool]:
    """
    List transactions for a budget with keyset pagination.

    Returns (transactions, has_more).
    """
    query = select(Transaction).where(Transaction.budget_id == budget_id)

    if account_id:
        query = query.where(Transaction.account_id == account_id)

    if payee_id:
        query = query.where(Transaction.payee_id == payee_id)

    if location_id:
        query = query.where(Transaction.location_id == location_id)

    # Filter by account's include_in_budget status
    if include_in_budget is not None:
        query = query.where(
            Transaction.account_id.in_(
                select(Account.id).where(
                    Account.budget_id == budget_id,
                    Account.include_in_budget == include_in_budget,
                )
            )
        )

    # Filter by reconciled status
    if is_reconciled is not None:
        query = query.where(Transaction.is_reconciled == is_reconciled)

    # Filter by envelope allocation
    if envelope_id:
        query = query.where(
            Transaction.id.in_(
                select(Allocation.transaction_id).where(
                    Allocation.budget_id == budget_id,
                    Allocation.envelope_id == envelope_id,
                    Allocation.transaction_id.isnot(None),
                )
            )
        )

    # Filter by status
    if status:
        query = query.where(Transaction.status.in_(status))
    else:
        # Default filtering: include posted, optionally scheduled, optionally skipped
        allowed_statuses = [TransactionStatus.POSTED]
        if include_scheduled:
            allowed_statuses.append(TransactionStatus.SCHEDULED)
        if include_skipped:
            allowed_statuses.append(TransactionStatus.SKIPPED)
        query = query.where(Transaction.status.in_(allowed_statuses))

    # Filter to expenses only (negative amounts)
    if expenses_only:
        query = query.where(Transaction.amount < 0)

    # Exclude adjustment transactions (starting balances, balance adjustments)
    if exclude_adjustments:
        query = query.where(Transaction.transaction_type != TransactionType.ADJUSTMENT)

    if cursor_date is not None and cursor_id is not None:
        # Keyset condition: (date, id) < (cursor_date, cursor_id)
        query = query.where(
            tuple_(Transaction.date, Transaction.id) < tuple_(cursor_date, cursor_id)
        )

    query = query.order_by(
        Transaction.date.desc(),
        Transaction.id.desc(),
    ).limit(limit + 1)  # Fetch one extra to detect has_more

    # Eagerly load allocations and linked transaction
    query = query.options(
        selectinload(Transaction.allocations),
        selectinload(Transaction.linked_transaction),
    )

    result = await session.execute(query)
    transactions = list(result.scalars().all())

    has_more = len(transactions) > limit
    if has_more:
        transactions = transactions[:limit]

    return transactions, has_more


async def count_unallocated_transactions(session: AsyncSession, budget_id: UUID) -> int:
    """Count expense transactions on budget accounts allocated to Unallocated.

    Excludes:
    - Income (positive amounts) - expected to be in Unallocated for distribution
    - Off-budget account transactions - not part of envelope budgeting
    - Adjustment transactions - accounting entries, not actual spending

    Returns the number of distinct expense transactions needing categorization.
    """
    unallocated_envelope = await get_unallocated_envelope(session, budget_id)
    if not unallocated_envelope:
        return 0

    result = await session.execute(
        select(func.count(distinct(Allocation.transaction_id)))
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id == unallocated_envelope.id,
            Allocation.transaction_id.isnot(None),
            Transaction.amount < 0,  # Only expenses need review
            Account.include_in_budget.is_(True),  # Only budget accounts
            Transaction.transaction_type
            != TransactionType.ADJUSTMENT,  # Exclude adjustments
        )
    )
    return result.scalar_one() or 0


async def get_transaction_by_id(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> Transaction:
    """Get a transaction by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.budget_id == budget_id)
        .options(
            selectinload(Transaction.allocations),
            selectinload(Transaction.linked_transaction),
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise TransactionNotFoundError(transaction_id)
    return transaction


async def _create_cc_envelope_moves(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
    transaction_date: DateType,
    cc_envelope_id: UUID,
    allocations: list[AllocationInput],
) -> list[Allocation]:
    """Create envelope move allocations for credit card transactions.

    For spending (negative amount): moves money from the expense envelope to
    the CC envelope (setting aside funds for payment).
    For refunds (positive amount): moves money from the CC envelope back to
    the target envelope (reversing a previous charge).

    Each allocation creates a paired move: one on the target envelope and one
    (opposite sign) on the CC envelope, keeping the net envelope change at zero.
    """
    from src.allocations.service import create_allocation

    group_id = uuid7()
    created_allocations = []
    execution_order = 0

    for alloc_input in allocations:
        # Create source allocation (spending envelope decreases)
        source_alloc = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=alloc_input.envelope_id,
            amount=alloc_input.amount,  # Negative for expense
            date=transaction_date,
            group_id=group_id,
            execution_order=execution_order,
            transaction_id=transaction_id,
            memo=alloc_input.memo,
        )
        created_allocations.append(source_alloc)
        execution_order += 1

        # Create destination allocation (CC envelope increases)
        dest_alloc = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=cc_envelope_id,
            amount=-alloc_input.amount,  # Positive (opposite of source)
            date=transaction_date,
            group_id=group_id,
            execution_order=execution_order,
            transaction_id=transaction_id,
            memo=None,
        )
        created_allocations.append(dest_alloc)
        execution_order += 1

    return created_allocations


async def create_transaction(
    session: AsyncSession, budget_id: UUID, transaction_in: TransactionCreate
) -> Transaction:
    """Create a new transaction for a budget.

    For budget accounts, allocations are required and must sum to the transaction amount.
    If no allocations are provided, defaults to the Unallocated envelope.
    Creates allocations and updates account balance.

    For credit card accounts with linked envelopes, spending and refund transactions
    create envelope moves instead of simple allocations - money moves between the
    target envelope and the CC envelope to keep envelope totals balanced.
    """
    # Get the account to check if it's a budget account
    account = await get_account_by_id(session, budget_id, transaction_in.account_id)

    # Check if this is a credit card transaction with a linked envelope
    is_cc_spending = (
        account.account_type == AccountType.CREDIT_CARD
        and transaction_in.amount < 0  # Expense
        and transaction_in.transaction_type == TransactionType.STANDARD
    )
    is_cc_refund = (
        account.account_type == AccountType.CREDIT_CARD
        and transaction_in.amount > 0  # Refund/credit
        and transaction_in.transaction_type == TransactionType.STANDARD
    )

    cc_envelope = None
    if is_cc_spending or is_cc_refund:
        cc_envelope = await get_cc_envelope_by_account_id(
            session, budget_id, account.id
        )
        # If no linked envelope (legacy CC account), fall through to standard behavior

    # Validate allocations for budget accounts (adjustment transactions are exempt)
    requires_allocations = (
        account.include_in_budget
        and transaction_in.transaction_type != TransactionType.ADJUSTMENT
    )

    # Handle allocations for budget accounts
    allocations = transaction_in.allocations
    if requires_allocations and not allocations:
        if transaction_in.amount < 0:
            # Expenses require explicit envelope allocation
            raise BadRequestError(
                "Envelope allocation is required for expenses in budget accounts"
            )
        else:
            # Income - check if we should auto-distribute via allocation rules
            if transaction_in.apply_allocation_rules:
                rule_allocations, remainder = await apply_rules_to_income(
                    session, budget_id, transaction_in.amount, transaction_in.date
                )
                if rule_allocations:
                    allocations = rule_allocations
                    if remainder > 0:
                        # Add remainder to Unallocated envelope
                        unallocated_envelope = await ensure_unallocated_envelope(
                            session, budget_id
                        )
                        allocations.append(
                            AllocationInput(
                                envelope_id=unallocated_envelope.id, amount=remainder
                            )
                        )
                else:
                    # No rules matched - fall back to Unallocated
                    unallocated_envelope = await ensure_unallocated_envelope(
                        session, budget_id
                    )
                    allocations = [
                        AllocationInput(
                            envelope_id=unallocated_envelope.id,
                            amount=transaction_in.amount,
                        )
                    ]
            else:
                # Default to Unallocated envelope (money waiting to be distributed)
                unallocated_envelope = await ensure_unallocated_envelope(
                    session, budget_id
                )
                allocations = [
                    AllocationInput(
                        envelope_id=unallocated_envelope.id,
                        amount=transaction_in.amount,
                    )
                ]

    # Validate allocation sum (only for non-CC-spending transactions)
    # CC spending creates zero-sum envelope moves, not transaction-matching allocations
    if requires_allocations and not cc_envelope:
        allocation_sum = sum(a.amount for a in allocations)
        if allocation_sum != transaction_in.amount:
            raise AllocationAmountMismatchError(transaction_in.amount, allocation_sum)

    transaction = Transaction(
        budget_id=budget_id,
        account_id=transaction_in.account_id,
        payee_id=transaction_in.payee_id,
        location_id=transaction_in.location_id,
        user_id=transaction_in.user_id,
        date=transaction_in.date,
        amount=transaction_in.amount,
        is_cleared=transaction_in.is_cleared,
        memo=transaction_in.memo,
        transaction_type=transaction_in.transaction_type,
    )
    session.add(transaction)
    await session.flush()

    # Create allocations
    if allocations:
        if cc_envelope:
            # CC transaction: create envelope moves instead of simple allocations
            await _create_cc_envelope_moves(
                session,
                budget_id,
                transaction.id,
                transaction.date,
                cc_envelope.id,
                allocations,
            )
        else:
            # Standard transaction: create normal allocations
            await create_allocations_for_transaction(
                session, budget_id, transaction.id, transaction.date, allocations
            )

    # Update account balance based on cleared status
    update_account_balance(account, transaction_in.amount, transaction_in.is_cleared)

    # Auto-set default envelope for payee if not already set
    # Use the first allocation's envelope as the default
    if transaction_in.payee_id and allocations:
        first_envelope_id = allocations[0].envelope_id
        if first_envelope_id:
            await payees_service.set_default_envelope_if_unset(
                session, budget_id, transaction_in.payee_id, first_envelope_id
            )

    await session.flush()

    # Re-fetch transaction with allocations eagerly loaded
    return await get_transaction_by_id(session, budget_id, transaction.id)


async def update_transaction(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
    transaction_in: TransactionUpdate,
) -> Transaction:
    """Update an existing transaction.

    For transfers, automatically mirrors changes to the linked transaction.
    If allocations are provided, replaces all existing allocations.
    """
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    # Store old is_cleared status for balance adjustment
    old_is_cleared = transaction.is_cleared

    # Handle allocation updates separately
    update_data = transaction_in.model_dump(exclude_unset=True)
    allocations = update_data.pop("allocations", None)

    for field, value in update_data.items():
        setattr(transaction, field, value)

    # Handle is_cleared change - move amount between balance fields
    if "is_cleared" in update_data and old_is_cleared != transaction.is_cleared:
        account = await get_account_by_id(session, budget_id, transaction.account_id)
        if transaction.is_cleared:
            # Moving from uncleared to cleared
            account.uncleared_balance -= transaction.amount
            account.cleared_balance += transaction.amount
        else:
            # Moving from cleared to uncleared
            account.cleared_balance -= transaction.amount
            account.uncleared_balance += transaction.amount

    # Mark as modified if this is a recurring transaction instance
    if transaction.recurring_transaction_id and (update_data or allocations):
        transaction.is_modified = True

    # For transfers, mirror shared fields to linked transaction
    if (
        transaction.transaction_type == TransactionType.TRANSFER
        and transaction.linked_transaction_id
    ):
        linked = await get_linked_transaction(session, budget_id, transaction_id)
        if linked:
            # Mirror shared fields (is_cleared excluded - each side clears independently)
            shared_fields = ["date", "memo", "user_id", "location_id"]
            for field in shared_fields:
                if field in update_data:
                    setattr(linked, field, update_data[field])
            # Mirror amount with opposite sign
            if "amount" in update_data:
                linked.amount = -transaction.amount
            # Mark linked as modified too if recurring
            if linked.recurring_transaction_id and (update_data or allocations):
                linked.is_modified = True

    # Handle allocation changes (not applicable for transfers)
    if (
        allocations is not None
        and transaction.transaction_type != TransactionType.TRANSFER
    ):
        account = await get_account_by_id(session, budget_id, transaction.account_id)
        if account.include_in_budget:
            # Check if this is a CC transaction (spending or refund)
            is_cc_transaction = (
                account.account_type == AccountType.CREDIT_CARD
                and transaction.amount != 0
                and transaction.transaction_type == TransactionType.STANDARD
            )

            cc_envelope = None
            if is_cc_transaction:
                cc_envelope = await get_cc_envelope_by_account_id(
                    session, budget_id, account.id
                )

            # Delete existing allocations
            await delete_allocations_for_transaction(session, budget_id, transaction_id)

            allocation_inputs = [
                AllocationInput(
                    envelope_id=a["envelope_id"],
                    amount=a["amount"],
                    memo=a.get("memo"),
                )
                for a in allocations
            ]

            if cc_envelope:
                # CC transaction: create envelope moves (target envelope <-> CC envelope)
                await _create_cc_envelope_moves(
                    session,
                    budget_id,
                    transaction_id,
                    transaction.date,
                    cc_envelope.id,
                    allocation_inputs,
                )
            else:
                # Standard transaction: validate sum and create normal allocations
                allocation_sum = sum(a["amount"] for a in allocations)
                if allocation_sum != transaction.amount:
                    raise AllocationAmountMismatchError(
                        transaction.amount, allocation_sum
                    )
                await create_allocations_for_transaction(
                    session,
                    budget_id,
                    transaction_id,
                    transaction.date,
                    allocation_inputs,
                )

    await session.flush()

    # Re-fetch to ensure allocations are loaded
    return await get_transaction_by_id(session, budget_id, transaction_id)


async def _claw_back_from_unallocated_transfers(
    session: AsyncSession, budget_id: UUID, deficit: int
) -> None:
    """Claw back one-sided transfer allocations from Unallocated to fix negative RTA.

    When income is allocated to Unallocated and then distributed to envelopes via
    one-sided transfers (e.g., "Auto Assign" or manual budgeting), those transfers
    have transaction_id=NULL and only a positive allocation on the destination
    envelope. If the income is later deleted, RTA goes negative because the
    one-sided transfers remain.

    This function finds and reduces/deletes those one-sided transfers (most recent
    first) until the deficit is covered.
    """
    # Find one-sided positive allocations (from Unallocated → envelope).
    # These have transaction_id=NULL, amount > 0, and NO matching negative
    # allocation in the same group (which would indicate an envelope-to-envelope
    # transfer between two regular envelopes).
    from sqlalchemy import exists
    from sqlalchemy.orm import aliased

    from src.envelopes.models import Envelope

    SiblingAlloc = aliased(Allocation)

    result = await session.execute(
        select(Allocation)
        .join(Envelope, Allocation.envelope_id == Envelope.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.transaction_id.is_(None),
            Allocation.amount > 0,
            Envelope.is_unallocated == False,  # noqa: E712
            ~exists(
                select(SiblingAlloc.id).where(
                    SiblingAlloc.group_id == Allocation.group_id,
                    SiblingAlloc.id != Allocation.id,
                    SiblingAlloc.amount < 0,
                    SiblingAlloc.budget_id == budget_id,
                )
            ),
        )
        .order_by(Allocation.date.desc(), Allocation.id.desc())
    )
    one_sided_allocations = list(result.scalars().all())

    remaining = deficit
    for allocation in one_sided_allocations:
        if remaining <= 0:
            break

        envelope = await session.get(Envelope, allocation.envelope_id)
        if not envelope:
            continue

        if allocation.amount <= remaining:
            # Delete entire allocation
            remaining -= allocation.amount
            envelope.current_balance -= allocation.amount
            await session.delete(allocation)
        else:
            # Partial reduction
            envelope.current_balance -= remaining
            allocation.amount -= remaining
            remaining = 0

    await session.flush()


async def delete_transaction(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> None:
    """Delete a transaction.

    For transfers, also deletes the linked transaction.
    Reverses envelope allocations and account balance changes.
    """
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    # Get account to update balance
    account = await get_account_by_id(session, budget_id, transaction.account_id)

    # Reverse envelope balances (cascade will delete allocations with transaction)
    await reverse_allocations_for_transaction(session, budget_id, transaction_id)

    # Reverse account balance change (only for POSTED - scheduled didn't affect balance)
    if transaction.status == TransactionStatus.POSTED:
        update_account_balance(account, -transaction.amount, transaction.is_cleared)

    # For transfers, also delete the linked transaction
    if (
        transaction.transaction_type == TransactionType.TRANSFER
        and transaction.linked_transaction_id
    ):
        linked = await get_linked_transaction(session, budget_id, transaction_id)
        if linked:
            # Reverse linked envelope balances and account balance
            linked_account = await get_account_by_id(
                session, budget_id, linked.account_id
            )
            await reverse_allocations_for_transaction(session, budget_id, linked.id)
            if linked.status == TransactionStatus.POSTED:
                update_account_balance(
                    linked_account, -linked.amount, linked.is_cleared
                )
            await session.delete(linked)

    await session.delete(transaction)
    await session.flush()

    # After all standard reversals, check if RTA went negative.
    # This happens when income allocated to Unallocated was subsequently
    # distributed to envelopes via one-sided transfers, then the income
    # was deleted — the transfer allocations remain, inflating envelopes.
    if account.include_in_budget and account.account_type != AccountType.CREDIT_CARD:
        rta = await calculate_unallocated_balance(session, budget_id)
        if rta < 0:
            await _claw_back_from_unallocated_transfers(session, budget_id, -rta)


async def skip_transaction(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> Transaction:
    """Skip a scheduled transaction.

    Only scheduled transactions can be skipped.
    """
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    if transaction.status != TransactionStatus.SCHEDULED:
        raise BadRequestError("Only scheduled transactions can be skipped")

    transaction.status = TransactionStatus.SKIPPED
    await session.flush()

    # Re-fetch to ensure allocations are loaded
    return await get_transaction_by_id(session, budget_id, transaction_id)


async def reset_transaction_to_template(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> Transaction:
    """Reset a recurring transaction instance to its template values.

    Only transactions linked to a recurring rule can be reset.
    """
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    if not transaction.recurring_transaction_id:
        raise BadRequestError("Transaction is not part of a recurring series")

    # Get the recurring rule
    result = await session.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == transaction.recurring_transaction_id
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise BadRequestError("Recurring transaction rule no longer exists")

    # Reset to template values
    transaction.amount = rule.amount
    transaction.payee_id = rule.payee_id
    transaction.account_id = rule.account_id
    transaction.location_id = rule.location_id
    transaction.memo = rule.memo
    transaction.is_modified = False

    await session.flush()

    # Re-fetch to ensure allocations are loaded
    return await get_transaction_by_id(session, budget_id, transaction_id)


async def mark_transactions_reconciled(
    session: AsyncSession,
    budget_id: UUID,
    account_id: UUID,
) -> int:
    """Mark all cleared, non-reconciled transactions as reconciled.

    Args:
        session: Database session
        budget_id: Budget ID
        account_id: Account ID

    Returns:
        Count of transactions marked as reconciled.
    """
    result = await session.execute(
        update(Transaction)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.account_id == account_id,
            Transaction.is_cleared == True,  # noqa: E712
            Transaction.is_reconciled == False,  # noqa: E712
        )
        .values(is_reconciled=True)
    )
    return result.rowcount


async def create_adjustment_transaction(
    session: AsyncSession,
    budget_id: UUID,
    account_id: UUID,
    amount: int,
    transaction_date: DateType | None = None,
    memo: str | None = None,
    is_reconciled: bool = False,
) -> Transaction:
    """Create an adjustment transaction for reconciliation.

    Adjustment transactions do not require allocations - they are for
    reconciling account balances, not envelope balances.

    Args:
        session: Database session
        budget_id: Budget ID
        account_id: Account to adjust
        amount: Adjustment amount (positive or negative)
        transaction_date: Date for the adjustment (defaults to today)
        memo: Optional memo for the adjustment
    """
    # Get account to update balance
    account = await get_account_by_id(session, budget_id, account_id)

    transaction = Transaction(
        budget_id=budget_id,
        account_id=account_id,
        payee_id=None,
        date=transaction_date or DateType.today(),
        amount=amount,
        is_cleared=True,
        is_reconciled=is_reconciled,
        memo=memo or "Balance adjustment",
        transaction_type=TransactionType.ADJUSTMENT,
        status=TransactionStatus.POSTED,
    )
    session.add(transaction)

    # Update account balance (adjustments are always cleared)
    account.cleared_balance += amount

    await session.flush()

    # Re-fetch transaction with allocations eagerly loaded
    return await get_transaction_by_id(session, budget_id, transaction.id)


# =============================================================================
# Transfer Functions
# =============================================================================


async def get_linked_transaction(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
) -> Transaction | None:
    """Get the linked transaction for a transfer."""
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    if not transaction.linked_transaction_id:
        return None

    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.id == transaction.linked_transaction_id,
            Transaction.budget_id == budget_id,
        )
        .options(
            selectinload(Transaction.allocations),
            selectinload(Transaction.linked_transaction),
        )
    )
    return result.scalar_one_or_none()


async def _handle_cc_payment(
    session: AsyncSession,
    budget_id: UUID,
    cc_account: Account,
    payment_amount: int,
    transaction_id: UUID,
) -> None:
    """Handle credit card payment envelope adjustment.

    When paying a CC, reduce the CC envelope balance. The reduction is
    capped at the envelope's current balance (can't go negative from payment).
    """
    from src.allocations.service import create_allocation

    cc_envelope = await get_cc_envelope_by_account_id(session, budget_id, cc_account.id)
    if not cc_envelope:
        return  # Legacy CC account without linked envelope

    # Calculate reduction amount (capped at current balance)
    reduction = min(payment_amount, max(0, cc_envelope.current_balance))

    if reduction > 0:
        # Create a negative allocation to reduce CC envelope
        # The money is "used" for its intended purpose (paying the CC)
        group_id = uuid7()
        await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=cc_envelope.id,
            amount=-reduction,
            date=DateType.today(),
            group_id=group_id,
            execution_order=0,
            transaction_id=transaction_id,
            memo="Credit card payment",
        )


async def create_transfer(
    session: AsyncSession,
    budget_id: UUID,
    transfer_in: TransferCreate,
) -> tuple[Transaction, Transaction]:
    """Create a transfer between two accounts.

    For budget -> tracking transfers, an envelope allocation is required to track
    where the money came from. For all other transfers, allocations are not needed.

    For transfers TO a credit card account (payments), automatically reduces
    the CC envelope balance to reflect funds used for payment.

    Returns (source_transaction, destination_transaction).
    """
    # Get both accounts (also verifies they belong to the budget)
    source_account = await get_account_by_id(
        session, budget_id, transfer_in.source_account_id
    )
    dest_account = await get_account_by_id(
        session, budget_id, transfer_in.destination_account_id
    )

    # Determine if this is a budget -> tracking transfer (money leaving budget)
    is_budget_to_tracking = (
        source_account.include_in_budget and not dest_account.include_in_budget
    )

    # Validate envelope is required for budget -> tracking transfers
    if is_budget_to_tracking and not transfer_in.envelope_id:
        raise BadRequestError(
            "envelope_id is required when transferring from a budget account "
            "to a tracking account"
        )

    # Create source transaction (negative amount - money leaving)
    source_txn = Transaction(
        budget_id=budget_id,
        account_id=transfer_in.source_account_id,
        payee_id=None,
        location_id=None,
        user_id=transfer_in.user_id,
        date=transfer_in.date,
        amount=-abs(transfer_in.amount),
        is_cleared=transfer_in.is_cleared,
        memo=transfer_in.memo,
        transaction_type=TransactionType.TRANSFER,
    )

    # Create destination transaction (positive amount - money arriving)
    dest_txn = Transaction(
        budget_id=budget_id,
        account_id=transfer_in.destination_account_id,
        payee_id=None,
        location_id=None,
        user_id=transfer_in.user_id,
        date=transfer_in.date,
        amount=abs(transfer_in.amount),
        is_cleared=transfer_in.is_cleared,
        memo=transfer_in.memo,
        transaction_type=TransactionType.TRANSFER,
    )

    session.add(source_txn)
    session.add(dest_txn)
    await session.flush()  # Insert rows before setting FK references

    # Link them bidirectionally
    source_txn.linked_transaction_id = dest_txn.id
    dest_txn.linked_transaction_id = source_txn.id

    # Update account balances based on cleared status
    update_account_balance(
        source_account, source_txn.amount, transfer_in.is_cleared
    )  # Negative
    update_account_balance(
        dest_account, dest_txn.amount, transfer_in.is_cleared
    )  # Positive

    # Create allocation for budget -> tracking transfers
    if is_budget_to_tracking and transfer_in.envelope_id:
        await create_allocations_for_transaction(
            session,
            budget_id,
            source_txn.id,
            source_txn.date,
            [
                AllocationInput(
                    envelope_id=transfer_in.envelope_id,
                    amount=source_txn.amount,  # Negative amount
                    memo=None,
                )
            ],
        )

    # Handle CC payment: reduce CC envelope when paying a credit card
    if dest_account.account_type == AccountType.CREDIT_CARD:
        await _handle_cc_payment(
            session, budget_id, dest_account, abs(transfer_in.amount), dest_txn.id
        )

    await session.flush()

    # Re-fetch transactions with allocations eagerly loaded
    source_txn = await get_transaction_by_id(session, budget_id, source_txn.id)
    dest_txn = await get_transaction_by_id(session, budget_id, dest_txn.id)

    return source_txn, dest_txn


async def update_transfer(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
    transfer_in: TransferUpdate,
) -> tuple[Transaction, Transaction]:
    """Update a transfer (both linked transactions).

    The transaction_id can be either side of the transfer.
    Returns (source_transaction, destination_transaction).
    """
    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    if transaction.transaction_type != TransactionType.TRANSFER:
        raise BadRequestError("Transaction is not a transfer")

    if not transaction.linked_transaction_id:
        raise BadRequestError("Transfer is missing linked transaction")

    linked = await get_linked_transaction(session, budget_id, transaction_id)
    if not linked:
        raise BadRequestError("Linked transaction not found")

    # Determine which is source (negative) and which is destination (positive)
    if transaction.amount < 0:
        source_txn, dest_txn = transaction, linked
    else:
        source_txn, dest_txn = linked, transaction

    # Store old values for balance adjustments
    old_source_account_id = source_txn.account_id
    old_dest_account_id = dest_txn.account_id
    old_source_amount = source_txn.amount
    old_dest_amount = dest_txn.amount
    old_source_is_cleared = source_txn.is_cleared
    old_dest_is_cleared = dest_txn.is_cleared

    update_data = transfer_in.model_dump(exclude_unset=True)

    # Apply all changes to source_txn first, flush, then dest_txn.
    # This avoids CircularDependencyError from SQLAlchemy when both
    # bidirectionally-linked transactions are dirty simultaneously.
    shared_fields = ["date", "memo", "user_id"]

    for field in shared_fields:
        if field in update_data:
            setattr(source_txn, field, update_data[field])
    if transfer_in.source_is_cleared is not None:
        source_txn.is_cleared = transfer_in.source_is_cleared
    if transfer_in.amount is not None:
        source_txn.amount = -abs(transfer_in.amount)
    if transfer_in.source_account_id is not None:
        await get_account_by_id(session, budget_id, transfer_in.source_account_id)
        source_txn.account_id = transfer_in.source_account_id

    await session.flush()

    for field in shared_fields:
        if field in update_data:
            setattr(dest_txn, field, update_data[field])
    if transfer_in.destination_is_cleared is not None:
        dest_txn.is_cleared = transfer_in.destination_is_cleared
    if transfer_in.amount is not None:
        dest_txn.amount = abs(transfer_in.amount)
    if transfer_in.destination_account_id is not None:
        await get_account_by_id(session, budget_id, transfer_in.destination_account_id)
        dest_txn.account_id = transfer_in.destination_account_id

    # Validate accounts are still different
    if source_txn.account_id == dest_txn.account_id:
        raise BadRequestError("Source and destination accounts must be different")

    await session.flush()

    # Determine what changed for balance recalculation
    source_cleared_changed = old_source_is_cleared != source_txn.is_cleared
    dest_cleared_changed = old_dest_is_cleared != dest_txn.is_cleared
    amount_or_accounts_changed = (
        transfer_in.amount is not None
        or transfer_in.source_account_id is not None
        or transfer_in.destination_account_id is not None
    )

    if amount_or_accounts_changed:
        # Full reverse-and-reapply when amounts or accounts change.
        old_source_account = await get_account_by_id(
            session, budget_id, old_source_account_id
        )
        old_dest_account = await get_account_by_id(
            session, budget_id, old_dest_account_id
        )
        update_account_balance(
            old_source_account, -old_source_amount, old_source_is_cleared
        )
        update_account_balance(old_dest_account, -old_dest_amount, old_dest_is_cleared)

        new_source_account = await get_account_by_id(
            session, budget_id, source_txn.account_id
        )
        new_dest_account = await get_account_by_id(
            session, budget_id, dest_txn.account_id
        )
        update_account_balance(
            new_source_account, source_txn.amount, source_txn.is_cleared
        )
        update_account_balance(new_dest_account, dest_txn.amount, dest_txn.is_cleared)
    else:
        # Only cleared status changed - move amounts between balance fields directly.
        if source_cleared_changed:
            source_account = await get_account_by_id(
                session, budget_id, source_txn.account_id
            )
            if source_txn.is_cleared:
                source_account.uncleared_balance -= source_txn.amount
                source_account.cleared_balance += source_txn.amount
            else:
                source_account.cleared_balance -= source_txn.amount
                source_account.uncleared_balance += source_txn.amount

        if dest_cleared_changed:
            dest_account = await get_account_by_id(
                session, budget_id, dest_txn.account_id
            )
            if dest_txn.is_cleared:
                dest_account.uncleared_balance -= dest_txn.amount
                dest_account.cleared_balance += dest_txn.amount
            else:
                dest_account.cleared_balance -= dest_txn.amount
                dest_account.uncleared_balance += dest_txn.amount

    # Handle envelope allocation for budget -> tracking transfers
    new_source_account = await get_account_by_id(
        session, budget_id, source_txn.account_id
    )
    new_dest_account = await get_account_by_id(session, budget_id, dest_txn.account_id)
    is_budget_to_tracking = (
        new_source_account.include_in_budget and not new_dest_account.include_in_budget
    )

    # Check if envelope_id was provided in the update
    envelope_id = transfer_in.envelope_id if "envelope_id" in update_data else None

    if is_budget_to_tracking:
        # Validate envelope is required for budget -> tracking
        if envelope_id is None and not source_txn.allocations:
            raise BadRequestError(
                "envelope_id is required when transferring from a budget account "
                "to a tracking account"
            )
        # Update allocation if envelope_id was provided
        if envelope_id is not None:
            # Delete existing allocations and create new one
            await delete_allocations_for_transaction(session, budget_id, source_txn.id)
            await create_allocations_for_transaction(
                session,
                budget_id,
                source_txn.id,
                source_txn.date,
                [
                    AllocationInput(
                        envelope_id=envelope_id,
                        amount=source_txn.amount,  # Negative amount
                        memo=None,
                    )
                ],
            )
    else:
        # Not budget -> tracking, remove any allocations on source transaction
        if source_txn.allocations:
            await delete_allocations_for_transaction(session, budget_id, source_txn.id)

    # Handle CC payment allocations when amount or accounts changed
    if amount_or_accounts_changed:
        # Reverse any existing CC payment allocations on dest transaction
        await delete_allocations_for_transaction(session, budget_id, dest_txn.id)

        # Re-apply CC payment if new dest is a CC account
        if new_dest_account.account_type == AccountType.CREDIT_CARD:
            await _handle_cc_payment(
                session,
                budget_id,
                new_dest_account,
                abs(dest_txn.amount),
                dest_txn.id,
            )

    # Mark both as modified if they are recurring transaction instances.
    # Flush between each to avoid circular dependency from bidirectional FKs.
    if source_txn.recurring_transaction_id and update_data:
        source_txn.is_modified = True
        await session.flush()
    if dest_txn.recurring_transaction_id and update_data:
        dest_txn.is_modified = True
        await session.flush()

    # Re-fetch transactions with allocations eagerly loaded
    source_txn = await get_transaction_by_id(session, budget_id, source_txn.id)
    dest_txn = await get_transaction_by_id(session, budget_id, dest_txn.id)

    return source_txn, dest_txn


async def delete_transfer(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
) -> None:
    """Delete a transfer (both linked transactions).

    Reverses envelope allocations and account balance changes for both sides.
    """
    from src.allocations.service import reverse_allocations_for_transaction

    transaction = await get_transaction_by_id(session, budget_id, transaction_id)

    if transaction.transaction_type != TransactionType.TRANSFER:
        raise BadRequestError("Transaction is not a transfer")

    linked = await get_linked_transaction(session, budget_id, transaction_id)

    # Reverse envelope balances for both transactions BEFORE deleting,
    # since cascade deletion would remove allocations before we can reverse them.
    await reverse_allocations_for_transaction(session, budget_id, transaction.id)
    if linked:
        await reverse_allocations_for_transaction(session, budget_id, linked.id)

    # Reverse account balance for this transaction
    account = await get_account_by_id(session, budget_id, transaction.account_id)
    update_account_balance(account, -transaction.amount, transaction.is_cleared)

    if linked:
        # Reverse account balance for linked transaction
        linked_account = await get_account_by_id(session, budget_id, linked.account_id)
        update_account_balance(linked_account, -linked.amount, linked.is_cleared)

    # Break bidirectional FK link before deleting to avoid CircularDependencyError.
    # Flush between each to avoid circular dependency from both being dirty.
    if linked:
        transaction.linked_transaction_id = None
        await session.flush()
        linked.linked_transaction_id = None
        await session.flush()

    await session.delete(transaction)
    await session.flush()
    if linked:
        await session.delete(linked)
        await session.flush()
