from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.locations import service
from src.locations.schemas import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter(prefix="/budgets/{budget_id}/locations", tags=["locations"])


@router.get(
    "",
    response_model=list[LocationResponse],
)
async def list_locations(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.LOCATIONS_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[LocationResponse]:
    locations = await service.list_locations(session, ctx.budget.id)
    return [LocationResponse.model_validate(location) for location in locations]


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.LOCATIONS_CREATE])
    ],
    location_in: LocationCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LocationResponse:
    location = await service.create_location(session, ctx.budget.id, location_in)
    return LocationResponse.model_validate(location)


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
)
async def get_location(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.LOCATIONS_READ])
    ],
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LocationResponse:
    location = await service.get_location_by_id(session, ctx.budget.id, location_id)
    return LocationResponse.model_validate(location)


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
)
async def update_location(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.LOCATIONS_UPDATE])
    ],
    location_id: UUID,
    location_in: LocationUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LocationResponse:
    location = await service.update_location(
        session, ctx.budget.id, location_id, location_in
    )
    return LocationResponse.model_validate(location)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_location(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.LOCATIONS_DELETE])
    ],
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_location(session, ctx.budget.id, location_id)
