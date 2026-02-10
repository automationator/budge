from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.recurring_transactions import service
from src.recurring_transactions.schemas import (
    RecurringTransactionCreate,
    RecurringTransactionResponse,
    RecurringTransactionUpdate,
)

router = APIRouter(
    prefix="/budgets/{budget_id}/recurring-transactions",
    tags=["recurring-transactions"],
)


@router.get(
    "",
    response_model=list[RecurringTransactionResponse],
)
async def list_recurring_transactions(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.RECURRING_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    include_inactive: Annotated[bool, Query()] = False,
) -> list[RecurringTransactionResponse]:
    """List all recurring transactions for a budget."""
    rules = await service.list_recurring_transactions(
        session,
        ctx.budget.id,
        include_inactive=include_inactive,
    )

    # Get next scheduled dates for all rules
    next_scheduled_dates = await service.get_next_scheduled_dates(
        session, [r.id for r in rules]
    )

    return [
        RecurringTransactionResponse(
            **{
                **RecurringTransactionResponse.model_validate(r).model_dump(),
                "next_scheduled_date": next_scheduled_dates.get(r.id),
            }
        )
        for r in rules
    ]


@router.post(
    "",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_transaction(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.RECURRING_CREATE])
    ],
    data: RecurringTransactionCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RecurringTransactionResponse:
    """Create a new recurring transaction.

    Automatically generates scheduled transaction instances up to 90 days ahead.
    """
    rule = await service.create_recurring_transaction(session, ctx.budget.id, data)
    next_scheduled_dates = await service.get_next_scheduled_dates(session, [rule.id])
    return RecurringTransactionResponse(
        **{
            **RecurringTransactionResponse.model_validate(rule).model_dump(),
            "next_scheduled_date": next_scheduled_dates.get(rule.id),
        }
    )


@router.get(
    "/{recurring_id}",
    response_model=RecurringTransactionResponse,
)
async def get_recurring_transaction(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.RECURRING_READ])
    ],
    recurring_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RecurringTransactionResponse:
    """Get a recurring transaction by ID."""
    rule = await service.get_recurring_transaction_by_id(
        session, ctx.budget.id, recurring_id
    )
    next_scheduled_dates = await service.get_next_scheduled_dates(session, [rule.id])
    return RecurringTransactionResponse(
        **{
            **RecurringTransactionResponse.model_validate(rule).model_dump(),
            "next_scheduled_date": next_scheduled_dates.get(rule.id),
        }
    )


@router.patch(
    "/{recurring_id}",
    response_model=RecurringTransactionResponse,
)
async def update_recurring_transaction(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.RECURRING_UPDATE])
    ],
    recurring_id: UUID,
    data: RecurringTransactionUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    propagate_to_future: Annotated[bool, Query()] = True,
) -> RecurringTransactionResponse:
    """Update a recurring transaction.

    By default, updates are propagated to unmodified scheduled transactions.
    Set propagate_to_future=false to only update the rule itself.
    """
    rule = await service.update_recurring_transaction(
        session,
        ctx.budget.id,
        recurring_id,
        data,
        propagate_to_future=propagate_to_future,
    )
    next_scheduled_dates = await service.get_next_scheduled_dates(session, [rule.id])
    return RecurringTransactionResponse(
        **{
            **RecurringTransactionResponse.model_validate(rule).model_dump(),
            "next_scheduled_date": next_scheduled_dates.get(rule.id),
        }
    )


@router.delete(
    "/{recurring_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recurring_transaction(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.RECURRING_DELETE])
    ],
    recurring_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    delete_scheduled: Annotated[bool, Query()] = True,
) -> None:
    """Delete a recurring transaction.

    By default, also deletes future scheduled occurrences.
    Set delete_scheduled=false to keep scheduled transactions (they become one-time).
    Posted transactions are always preserved.
    """
    await service.delete_recurring_transaction(
        session,
        ctx.budget.id,
        recurring_id,
        delete_scheduled=delete_scheduled,
    )
