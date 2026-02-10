from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.exceptions import BadRequestError
from src.pagination import CursorPage, decode_cursor, encode_cursor
from src.recurring_transactions.service import process_recurring
from src.transactions import service
from src.transactions.models import TransactionStatus, TransactionType
from src.transactions.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    TransferCreate,
    TransferResponse,
    TransferUpdate,
)

router = APIRouter(prefix="/budgets/{budget_id}/transactions", tags=["transactions"])


@router.get(
    "",
    response_model=CursorPage[TransactionResponse],
)
async def list_transactions(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query()] = None,
    account_id: Annotated[UUID | None, Query()] = None,
    envelope_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[
        list[TransactionStatus] | None, Query(alias="status")
    ] = None,
    include_scheduled: Annotated[bool, Query()] = True,
    include_skipped: Annotated[bool, Query()] = False,
    is_reconciled: Annotated[bool | None, Query()] = None,
    include_in_budget: Annotated[bool | None, Query()] = None,
    payee_id: Annotated[UUID | None, Query()] = None,
    location_id: Annotated[UUID | None, Query()] = None,
    expenses_only: Annotated[bool, Query()] = False,
    exclude_adjustments: Annotated[bool, Query()] = False,
) -> CursorPage[TransactionResponse]:
    # Process recurring transactions (realize due, ensure horizon)
    await process_recurring(session, ctx.budget.id)

    decoded = decode_cursor(cursor) if cursor else None

    transactions, has_more = await service.list_transactions(
        session,
        ctx.budget.id,
        limit=limit,
        cursor_date=decoded.date if decoded else None,
        cursor_id=decoded.id if decoded else None,
        account_id=account_id,
        envelope_id=envelope_id,
        status=status_filter,
        include_scheduled=include_scheduled,
        include_skipped=include_skipped,
        is_reconciled=is_reconciled,
        include_in_budget=include_in_budget,
        payee_id=payee_id,
        location_id=location_id,
        expenses_only=expenses_only,
        exclude_adjustments=exclude_adjustments,
    )

    next_cursor = None
    if has_more and transactions:
        last = transactions[-1]
        next_cursor = encode_cursor(last.date, last.id)

    return CursorPage(
        items=[TransactionResponse.model_validate(txn) for txn in transactions],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/unallocated-count")
async def get_unallocated_count(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    """Get count of transactions allocated to the Unallocated envelope."""
    count = await service.count_unallocated_transactions(session, ctx.budget.id)
    return {"count": count}


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_CREATE]),
    ],
    transaction_in: TransactionCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionResponse:
    transaction = await service.create_transaction(
        session, ctx.budget.id, transaction_in
    )
    return TransactionResponse.model_validate(transaction)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
async def get_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionResponse:
    transaction = await service.get_transaction_by_id(
        session, ctx.budget.id, transaction_id
    )
    return TransactionResponse.model_validate(transaction)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
async def update_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_UPDATE]),
    ],
    transaction_id: UUID,
    transaction_in: TransactionUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionResponse:
    transaction = await service.update_transaction(
        session, ctx.budget.id, transaction_id, transaction_in
    )
    return TransactionResponse.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_DELETE]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_transaction(session, ctx.budget.id, transaction_id)


@router.post(
    "/{transaction_id}/skip",
    response_model=TransactionResponse,
)
async def skip_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_UPDATE]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionResponse:
    """Skip a scheduled recurring transaction.

    Marks the transaction as skipped so it won't be included in balance calculations.
    Only scheduled transactions can be skipped.
    """
    transaction = await service.skip_transaction(session, ctx.budget.id, transaction_id)
    return TransactionResponse.model_validate(transaction)


@router.post(
    "/{transaction_id}/reset",
    response_model=TransactionResponse,
)
async def reset_transaction(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_UPDATE]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionResponse:
    """Reset a recurring transaction instance to its template values.

    Reverts any user modifications and sets is_modified back to false.
    Only transactions linked to a recurring rule can be reset.
    """
    transaction = await service.reset_transaction_to_template(
        session, ctx.budget.id, transaction_id
    )
    return TransactionResponse.model_validate(transaction)


# =============================================================================
# Transfer Endpoints
# =============================================================================


@router.post(
    "/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_CREATE]),
    ],
    transfer_in: TransferCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransferResponse:
    """Create a transfer between two accounts.

    Creates two linked transactions: one debiting the source account (negative)
    and one crediting the destination account (positive).
    """
    source_txn, dest_txn = await service.create_transfer(
        session, ctx.budget.id, transfer_in
    )
    return TransferResponse(
        source_transaction=TransactionResponse.model_validate(source_txn),
        destination_transaction=TransactionResponse.model_validate(dest_txn),
    )


@router.get(
    "/transfers/{transaction_id}",
    response_model=TransferResponse,
)
async def get_transfer(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransferResponse:
    """Get a transfer by either transaction ID.

    Returns both sides of the transfer.
    """
    transaction = await service.get_transaction_by_id(
        session, ctx.budget.id, transaction_id
    )

    if transaction.transaction_type != TransactionType.TRANSFER:
        raise BadRequestError("Transaction is not a transfer")

    linked = await service.get_linked_transaction(
        session, ctx.budget.id, transaction_id
    )
    if not linked:
        raise BadRequestError("Transfer is missing linked transaction")

    # Determine source (negative) and destination (positive)
    if transaction.amount < 0:
        source_txn, dest_txn = transaction, linked
    else:
        source_txn, dest_txn = linked, transaction

    return TransferResponse(
        source_transaction=TransactionResponse.model_validate(source_txn),
        destination_transaction=TransactionResponse.model_validate(dest_txn),
    )


@router.patch(
    "/transfers/{transaction_id}",
    response_model=TransferResponse,
)
async def update_transfer(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_UPDATE]),
    ],
    transaction_id: UUID,
    transfer_in: TransferUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransferResponse:
    """Update a transfer (updates both linked transactions).

    The transaction_id can be either side of the transfer.
    """
    source_txn, dest_txn = await service.update_transfer(
        session, ctx.budget.id, transaction_id, transfer_in
    )
    return TransferResponse(
        source_transaction=TransactionResponse.model_validate(source_txn),
        destination_transaction=TransactionResponse.model_validate(dest_txn),
    )


@router.delete(
    "/transfers/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_transfer(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_DELETE]),
    ],
    transaction_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Delete a transfer (deletes both linked transactions)."""
    await service.delete_transfer(session, ctx.budget.id, transaction_id)
