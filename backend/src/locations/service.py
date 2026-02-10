from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.locations.exceptions import DuplicateLocationNameError, LocationNotFoundError
from src.locations.models import Location
from src.locations.schemas import LocationCreate, LocationUpdate


async def list_locations(session: AsyncSession, budget_id: UUID) -> list[Location]:
    """List all locations for a budget, ordered by name."""
    result = await session.execute(
        select(Location).where(Location.budget_id == budget_id).order_by(Location.name)
    )
    return list(result.scalars().all())


async def get_location_by_id(
    session: AsyncSession, budget_id: UUID, location_id: UUID
) -> Location:
    """Get a location by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Location).where(
            Location.id == location_id, Location.budget_id == budget_id
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise LocationNotFoundError(location_id)
    return location


async def create_location(
    session: AsyncSession, budget_id: UUID, location_in: LocationCreate
) -> Location:
    """Create a new location for a budget."""
    location = Location(
        budget_id=budget_id,
        name=location_in.name,
        icon=location_in.icon,
        description=location_in.description,
    )
    session.add(location)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_location_name" in str(e):
            raise DuplicateLocationNameError(location_in.name) from e
        raise
    return location


async def update_location(
    session: AsyncSession,
    budget_id: UUID,
    location_id: UUID,
    location_in: LocationUpdate,
) -> Location:
    """Update an existing location."""
    location = await get_location_by_id(session, budget_id, location_id)

    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_location_name" in str(e):
            raise DuplicateLocationNameError(location_in.name or location.name) from e
        raise
    return location


async def delete_location(
    session: AsyncSession, budget_id: UUID, location_id: UUID
) -> None:
    """Delete a location."""
    location = await get_location_by_id(session, budget_id, location_id)
    await session.delete(location)
    await session.flush()
