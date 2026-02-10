from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.envelope_groups import service
from src.envelope_groups.schemas import (
    EnvelopeGroupCreate,
    EnvelopeGroupResponse,
    EnvelopeGroupUpdate,
)

router = APIRouter(
    prefix="/budgets/{budget_id}/envelope-groups", tags=["envelope-groups"]
)


@router.get(
    "",
    response_model=list[EnvelopeGroupResponse],
)
async def list_envelope_groups(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPE_GROUPS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[EnvelopeGroupResponse]:
    groups = await service.list_envelope_groups(session, ctx.budget.id)
    return [EnvelopeGroupResponse.model_validate(group) for group in groups]


@router.post(
    "",
    response_model=EnvelopeGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_envelope_group(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPE_GROUPS_CREATE]),
    ],
    envelope_group_in: EnvelopeGroupCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeGroupResponse:
    group = await service.create_envelope_group(
        session, ctx.budget.id, envelope_group_in
    )
    return EnvelopeGroupResponse.model_validate(group)


@router.get(
    "/{envelope_group_id}",
    response_model=EnvelopeGroupResponse,
)
async def get_envelope_group(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPE_GROUPS_READ]),
    ],
    envelope_group_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeGroupResponse:
    group = await service.get_envelope_group_by_id(
        session, ctx.budget.id, envelope_group_id
    )
    return EnvelopeGroupResponse.model_validate(group)


@router.patch(
    "/{envelope_group_id}",
    response_model=EnvelopeGroupResponse,
)
async def update_envelope_group(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPE_GROUPS_UPDATE]),
    ],
    envelope_group_id: UUID,
    envelope_group_in: EnvelopeGroupUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeGroupResponse:
    group = await service.update_envelope_group(
        session, ctx.budget.id, envelope_group_id, envelope_group_in
    )
    return EnvelopeGroupResponse.model_validate(group)


@router.delete(
    "/{envelope_group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_envelope_group(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPE_GROUPS_DELETE]),
    ],
    envelope_group_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_envelope_group(session, ctx.budget.id, envelope_group_id)
