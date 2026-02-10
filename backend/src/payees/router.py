from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.payees import service
from src.payees.schemas import (
    DefaultEnvelopeResponse,
    PayeeCreate,
    PayeeResponse,
    PayeeUpdate,
)

router = APIRouter(prefix="/budgets/{budget_id}/payees", tags=["payees"])


@router.get(
    "",
    response_model=list[PayeeResponse],
)
async def list_payees(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[PayeeResponse]:
    payees = await service.list_payees(session, ctx.budget.id)
    return [PayeeResponse.model_validate(payee) for payee in payees]


@router.post(
    "",
    response_model=PayeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payee(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_CREATE])
    ],
    payee_in: PayeeCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PayeeResponse:
    payee = await service.create_payee(session, ctx.budget.id, payee_in)
    return PayeeResponse.model_validate(payee)


@router.get(
    "/{payee_id}",
    response_model=PayeeResponse,
)
async def get_payee(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_READ])
    ],
    payee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PayeeResponse:
    payee = await service.get_payee_by_id(session, ctx.budget.id, payee_id)
    return PayeeResponse.model_validate(payee)


@router.patch(
    "/{payee_id}",
    response_model=PayeeResponse,
)
async def update_payee(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_UPDATE])
    ],
    payee_id: UUID,
    payee_in: PayeeUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PayeeResponse:
    payee = await service.update_payee(session, ctx.budget.id, payee_id, payee_in)
    return PayeeResponse.model_validate(payee)


@router.delete(
    "/{payee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_payee(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_DELETE])
    ],
    payee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_payee(session, ctx.budget.id, payee_id)


@router.get(
    "/{payee_id}/default-envelope",
    response_model=DefaultEnvelopeResponse,
)
async def get_default_envelope(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.PAYEES_READ])
    ],
    payee_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DefaultEnvelopeResponse:
    """Get default envelope for a payee.

    Returns the payee's default envelope, which is auto-filled when creating
    new transactions with this payee.
    """
    envelope_id = await service.get_default_envelope(session, ctx.budget.id, payee_id)
    return DefaultEnvelopeResponse(envelope_id=envelope_id)
