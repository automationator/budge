from datetime import date as DateType
from uuid import UUID, uuid7

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.allocations.exceptions import (
    AllocationAmountMismatchError,
    AllocationNotFoundError,
    SameEnvelopeTransferError,
)
from src.allocations.models import Allocation
from src.allocations.schemas import AllocationInput, AllocationUpdate
from src.envelopes.exceptions import EnvelopeNotFoundError
from src.envelopes.models import Envelope
from src.envelopes.service import validate_unallocated_has_funds
from src.transactions.models import Transaction


async def get_envelope_by_id(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID
) -> Envelope:
    """Get an envelope by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Envelope).where(
            Envelope.id == envelope_id, Envelope.budget_id == budget_id
        )
    )
    envelope = result.scalar_one_or_none()
    if not envelope:
        raise EnvelopeNotFoundError(envelope_id)
    return envelope


async def get_allocation_by_id(
    session: AsyncSession, budget_id: UUID, allocation_id: UUID
) -> Allocation:
    """Get an allocation by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Allocation).where(
            Allocation.id == allocation_id, Allocation.budget_id == budget_id
        )
    )
    allocation = result.scalar_one_or_none()
    if not allocation:
        raise AllocationNotFoundError(allocation_id)
    return allocation


async def list_allocations_for_envelope(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID
) -> list[Allocation]:
    """List all allocations for an envelope, ordered by date then amount."""
    result = await session.execute(
        select(Allocation)
        .where(Allocation.budget_id == budget_id, Allocation.envelope_id == envelope_id)
        .options(selectinload(Allocation.transaction))  # Eager load for response
        .order_by(Allocation.date.desc(), Allocation.amount.desc())
    )
    return list(result.scalars().all())


async def list_allocations_for_transaction(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> list[Allocation]:
    """List all allocations for a transaction, ordered by execution order."""
    result = await session.execute(
        select(Allocation)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.transaction_id == transaction_id,
        )
        .order_by(Allocation.execution_order)
    )
    return list(result.scalars().all())


async def create_allocation(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    amount: int,
    date: DateType,
    group_id: UUID,
    execution_order: int,
    transaction_id: UUID | None = None,
    memo: str | None = None,
    allocation_rule_id: UUID | None = None,
) -> Allocation:
    """Create a single allocation and update the envelope balance.

    For unallocated envelopes, the balance is not updated since it's
    calculated dynamically.
    """
    # Verify envelope exists and belongs to budget
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)

    allocation = Allocation(
        budget_id=budget_id,
        envelope_id=envelope_id,
        transaction_id=transaction_id,
        allocation_rule_id=allocation_rule_id,
        group_id=group_id,
        execution_order=execution_order,
        amount=amount,
        date=date,
        memo=memo,
    )
    session.add(allocation)

    # Update envelope balance (skip for unallocated - it's calculated dynamically)
    if not envelope.is_unallocated:
        envelope.current_balance += amount

    await session.flush()
    return allocation


async def create_allocations_for_transaction(
    session: AsyncSession,
    budget_id: UUID,
    transaction_id: UUID,
    transaction_date: DateType,
    allocations: list[AllocationInput],
) -> list[Allocation]:
    """Create multiple allocations for a transaction."""
    group_id = uuid7()
    created_allocations = []

    for i, alloc_input in enumerate(allocations):
        allocation = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=alloc_input.envelope_id,
            amount=alloc_input.amount,
            date=transaction_date,
            group_id=group_id,
            execution_order=i,
            transaction_id=transaction_id,
            memo=alloc_input.memo,
            allocation_rule_id=alloc_input.allocation_rule_id,
        )
        created_allocations.append(allocation)

    return created_allocations


async def delete_allocation(
    session: AsyncSession, budget_id: UUID, allocation_id: UUID
) -> None:
    """Delete an allocation and reverse the envelope balance change.

    For unallocated envelopes, the balance is not updated since it's
    calculated dynamically.
    """
    allocation = await get_allocation_by_id(session, budget_id, allocation_id)

    # Reverse the envelope balance change (skip for unallocated)
    envelope = await get_envelope_by_id(session, budget_id, allocation.envelope_id)
    if not envelope.is_unallocated:
        envelope.current_balance -= allocation.amount

    await session.delete(allocation)
    await session.flush()


async def update_allocation(
    session: AsyncSession,
    budget_id: UUID,
    allocation_id: UUID,
    allocation_in: AllocationUpdate,
) -> Allocation:
    """Update an allocation.

    Handles envelope balance adjustments when envelope_id or amount changes.
    Validates that allocations still sum to transaction amount if linked to a transaction.
    """
    allocation = await get_allocation_by_id(session, budget_id, allocation_id)
    old_envelope_id = allocation.envelope_id
    old_amount = allocation.amount

    update_data = allocation_in.model_dump(exclude_unset=True)

    # Handle envelope change
    new_envelope_id = update_data.get("envelope_id", old_envelope_id)
    new_amount = update_data.get("amount", old_amount)

    # Validate new amount if allocation is linked to a transaction
    if "amount" in update_data and allocation.transaction_id:
        # Get the transaction to check the expected total
        result = await session.execute(
            select(Transaction).where(
                Transaction.id == allocation.transaction_id,
                Transaction.budget_id == budget_id,
            )
        )
        transaction = result.scalar_one_or_none()
        if transaction:
            # Get all allocations for this transaction and calculate new sum
            all_allocations = await list_allocations_for_transaction(
                session, budget_id, allocation.transaction_id
            )
            new_sum = sum(
                new_amount if a.id == allocation_id else a.amount
                for a in all_allocations
            )
            if new_sum != transaction.amount:
                raise AllocationAmountMismatchError(transaction.amount, new_sum)

    # Update envelope balances if envelope or amount changed
    # (skip balance updates for unallocated envelopes - calculated dynamically)
    if new_envelope_id != old_envelope_id or new_amount != old_amount:
        # Reverse old envelope balance
        old_envelope = await get_envelope_by_id(session, budget_id, old_envelope_id)
        if not old_envelope.is_unallocated:
            old_envelope.current_balance -= old_amount

        # Apply to new envelope (might be same envelope if only amount changed)
        new_envelope = await get_envelope_by_id(session, budget_id, new_envelope_id)
        if not new_envelope.is_unallocated:
            new_envelope.current_balance += new_amount

    # Apply updates to allocation
    for field, value in update_data.items():
        setattr(allocation, field, value)

    await session.flush()
    return allocation


async def reverse_allocations_for_transaction(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> None:
    """Reverse envelope balances for all allocations of a transaction.

    Does NOT delete the allocations - use this when the transaction cascade
    will handle allocation deletion.

    For unallocated envelopes, the balance is not updated since it's
    calculated dynamically.
    """
    allocations = await list_allocations_for_transaction(
        session, budget_id, transaction_id
    )

    for allocation in allocations:
        envelope = await get_envelope_by_id(session, budget_id, allocation.envelope_id)
        if not envelope.is_unallocated:
            envelope.current_balance -= allocation.amount

    await session.flush()


async def delete_allocations_for_transaction(
    session: AsyncSession, budget_id: UUID, transaction_id: UUID
) -> None:
    """Delete all allocations for a transaction and reverse envelope balances.

    Use reverse_allocations_for_transaction instead if the transaction will be
    deleted (cascade handles allocation deletion).

    For unallocated envelopes, the balance is not updated since it's
    calculated dynamically.
    """
    allocations = await list_allocations_for_transaction(
        session, budget_id, transaction_id
    )

    for allocation in allocations:
        # Reverse the envelope balance change (skip for unallocated)
        envelope = await get_envelope_by_id(session, budget_id, allocation.envelope_id)
        if not envelope.is_unallocated:
            envelope.current_balance -= allocation.amount
        await session.delete(allocation)

    await session.flush()


async def create_envelope_transfer(
    session: AsyncSession,
    budget_id: UUID,
    source_envelope_id: UUID,
    destination_envelope_id: UUID,
    amount: int,
    memo: str | None = None,
    transfer_date: DateType | None = None,
) -> tuple[Allocation | None, Allocation | None]:
    """Transfer money between envelopes.

    For transfers involving the unallocated envelope, only one allocation is
    created (for the non-unallocated side). The unallocated balance is calculated
    dynamically, so we only need to track the regular envelope's balance change.

    Returns (source_allocation, destination_allocation). One may be None if
    that side is the unallocated envelope.
    """
    if source_envelope_id == destination_envelope_id:
        raise SameEnvelopeTransferError()

    source_envelope = await get_envelope_by_id(session, budget_id, source_envelope_id)
    dest_envelope = await get_envelope_by_id(
        session, budget_id, destination_envelope_id
    )

    # Default to today if no date provided
    allocation_date = transfer_date if transfer_date is not None else DateType.today()

    group_id = uuid7()
    source_allocation = None
    dest_allocation = None

    if source_envelope.is_unallocated:
        # Transferring FROM unallocated: validate funds, create only dest allocation
        await validate_unallocated_has_funds(session, budget_id, abs(amount))
        dest_allocation = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=destination_envelope_id,
            amount=abs(amount),
            date=allocation_date,
            group_id=group_id,
            execution_order=0,
            transaction_id=None,
            memo=memo,
        )
    elif dest_envelope.is_unallocated:
        # Transferring TO unallocated: create only source allocation
        source_allocation = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=source_envelope_id,
            amount=-abs(amount),
            date=allocation_date,
            group_id=group_id,
            execution_order=0,
            transaction_id=None,
            memo=memo,
        )
    else:
        # Regular transfer: create both allocations
        source_allocation = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=source_envelope_id,
            amount=-abs(amount),
            date=allocation_date,
            group_id=group_id,
            execution_order=0,
            transaction_id=None,
            memo=memo,
        )
        dest_allocation = await create_allocation(
            session=session,
            budget_id=budget_id,
            envelope_id=destination_envelope_id,
            amount=abs(amount),
            date=allocation_date,
            group_id=group_id,
            execution_order=1,
            transaction_id=None,
            memo=memo,
        )

    return source_allocation, dest_allocation
