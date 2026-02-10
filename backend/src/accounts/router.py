from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts import service
from src.accounts.schemas import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    BalanceCorrectionResponse,
)
from src.allocations.schemas import AllocationInput
from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.envelopes.service import ensure_unallocated_envelope
from src.transactions.models import TransactionType
from src.transactions.schemas import (
    ReconcileRequest,
    ReconcileResponse,
    TransactionCreate,
    TransactionResponse,
)
from src.transactions.service import create_transaction, mark_transactions_reconciled

router = APIRouter(prefix="/budgets/{budget_id}/accounts", tags=["accounts"])


@router.get(
    "",
    response_model=list[AccountResponse],
)
async def list_accounts(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ACCOUNTS_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[AccountResponse]:
    accounts = await service.list_accounts(session, ctx.budget.id)
    return [AccountResponse.model_validate(account) for account in accounts]


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ACCOUNTS_CREATE])
    ],
    account_in: AccountCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AccountResponse:
    account = await service.create_account(session, ctx.budget.id, account_in)
    return AccountResponse.model_validate(account)


@router.post(
    "/recalculate-balances",
    response_model=list[BalanceCorrectionResponse],
)
async def recalculate_balances(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.DATA_REPAIR])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[BalanceCorrectionResponse]:
    """Recalculate all account balances from POSTED transactions.

    Use this to fix account balances corrupted by the SCHEDULED transaction deletion bug.
    Requires owner permissions (data:repair scope).
    """
    corrections = await service.recalculate_account_balances(session, ctx.budget.id)
    return [BalanceCorrectionResponse(**c) for c in corrections]


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
)
async def get_account(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ACCOUNTS_READ])
    ],
    account_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AccountResponse:
    account = await service.get_account_by_id(session, ctx.budget.id, account_id)
    return AccountResponse.model_validate(account)


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
)
async def update_account(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ACCOUNTS_UPDATE])
    ],
    account_id: UUID,
    account_in: AccountUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AccountResponse:
    account = await service.update_account(
        session, ctx.budget.id, account_id, account_in
    )
    return AccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ACCOUNTS_DELETE])
    ],
    account_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_account(session, ctx.budget.id, account_id)


@router.post(
    "/{account_id}/reconcile",
    response_model=ReconcileResponse,
    status_code=status.HTTP_200_OK,
)
async def reconcile_account(
    ctx: Annotated[
        BudgetContext,
        Security(
            BudgetSecurity(),
            scopes=[BudgetScope.ACCOUNTS_UPDATE, BudgetScope.TRANSACTIONS_CREATE],
        ),
    ],
    account_id: UUID,
    reconcile_in: ReconcileRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReconcileResponse:
    """Reconcile an account balance.

    Marks all cleared transactions as reconciled. If the actual balance
    differs from the current cleared balance, creates an adjustment transaction.
    The adjustment is allocated to the unallocated envelope.
    """
    account = await service.get_account_by_id(session, ctx.budget.id, account_id)

    # Mark all cleared transactions as reconciled
    reconciled_count = await mark_transactions_reconciled(
        session, ctx.budget.id, account_id
    )

    # Update last reconciled timestamp
    account.last_reconciled_at = datetime.now(UTC)
    await session.flush()

    difference = reconcile_in.actual_balance - account.cleared_balance

    adjustment_transaction = None
    if difference != 0:
        # Get the unallocated envelope to allocate the adjustment
        unallocated_envelope = await ensure_unallocated_envelope(session, ctx.budget.id)

        # Create adjustment transaction with allocation to unallocated envelope
        # The adjustment is already reconciled since it's created during reconciliation
        transaction_in = TransactionCreate(
            account_id=account_id,
            payee_id=None,
            date=date.today(),
            amount=difference,
            is_cleared=True,
            memo="Balance adjustment",
            transaction_type=TransactionType.ADJUSTMENT,
            allocations=[
                AllocationInput(envelope_id=unallocated_envelope.id, amount=difference)
            ],
        )

        transaction = await create_transaction(session, ctx.budget.id, transaction_in)
        # Mark the adjustment transaction as reconciled
        transaction.is_reconciled = True
        await session.flush()
        adjustment_transaction = TransactionResponse.model_validate(transaction)
        reconciled_count += 1  # Include the adjustment in the count

    return ReconcileResponse(
        transactions_reconciled=reconciled_count,
        adjustment_transaction=adjustment_transaction,
    )
