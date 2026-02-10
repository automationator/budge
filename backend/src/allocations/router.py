from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.allocations import service
from src.allocations.schemas import (
    AllocationResponse,
    AllocationUpdate,
    EnvelopeTransferCreate,
    EnvelopeTransferResponse,
)
from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session

router = APIRouter(prefix="/budgets/{budget_id}/allocations", tags=["allocations"])


@router.get(
    "",
    response_model=list[AllocationResponse],
)
async def list_allocations(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATIONS_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    envelope_id: Annotated[UUID | None, Query()] = None,
    transaction_id: Annotated[UUID | None, Query()] = None,
) -> list[AllocationResponse]:
    """List allocations, optionally filtered by envelope or transaction."""
    if envelope_id:
        allocations = await service.list_allocations_for_envelope(
            session, ctx.budget.id, envelope_id
        )
    elif transaction_id:
        allocations = await service.list_allocations_for_transaction(
            session, ctx.budget.id, transaction_id
        )
    else:
        # Default: return empty list (require a filter)
        # Could also return all allocations, but that could be a lot
        allocations = []

    return [AllocationResponse.model_validate(a) for a in allocations]


@router.get(
    "/{allocation_id}",
    response_model=AllocationResponse,
)
async def get_allocation(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATIONS_READ])
    ],
    allocation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationResponse:
    allocation = await service.get_allocation_by_id(
        session, ctx.budget.id, allocation_id
    )
    return AllocationResponse.model_validate(allocation)


@router.patch(
    "/{allocation_id}",
    response_model=AllocationResponse,
)
async def update_allocation(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATIONS_UPDATE]),
    ],
    allocation_id: UUID,
    allocation_in: AllocationUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationResponse:
    """Update an allocation.

    Can update envelope_id, amount, or memo.
    Envelope balances are automatically adjusted when envelope or amount changes.
    If the allocation is linked to a transaction, the sum of all allocations
    must still equal the transaction amount.
    """
    allocation = await service.update_allocation(
        session=session,
        budget_id=ctx.budget.id,
        allocation_id=allocation_id,
        allocation_in=allocation_in,
    )
    return AllocationResponse.model_validate(allocation)


@router.post(
    "/envelope-transfer",
    response_model=EnvelopeTransferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_envelope_transfer(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATIONS_CREATE]),
    ],
    transfer_in: EnvelopeTransferCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeTransferResponse:
    """Transfer money between envelopes.

    This creates two allocations: one negative (source) and one positive (destination).
    No transaction is created since this is purely a budget reallocation.
    """
    source_alloc, dest_alloc = await service.create_envelope_transfer(
        session=session,
        budget_id=ctx.budget.id,
        source_envelope_id=transfer_in.source_envelope_id,
        destination_envelope_id=transfer_in.destination_envelope_id,
        amount=transfer_in.amount,
        memo=transfer_in.memo,
        transfer_date=transfer_in.date,
    )
    return EnvelopeTransferResponse(
        source_allocation=AllocationResponse.model_validate(source_alloc)
        if source_alloc
        else None,
        destination_allocation=AllocationResponse.model_validate(dest_alloc)
        if dest_alloc
        else None,
    )
