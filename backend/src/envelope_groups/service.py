from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.envelope_groups.exceptions import (
    DuplicateEnvelopeGroupNameError,
    EnvelopeGroupNotFoundError,
)
from src.envelope_groups.models import EnvelopeGroup
from src.envelope_groups.schemas import EnvelopeGroupCreate, EnvelopeGroupUpdate


async def list_envelope_groups(
    session: AsyncSession, budget_id: UUID
) -> list[EnvelopeGroup]:
    """List all envelope groups for a budget, ordered by sort_order then name."""
    result = await session.execute(
        select(EnvelopeGroup)
        .where(EnvelopeGroup.budget_id == budget_id)
        .order_by(EnvelopeGroup.sort_order, EnvelopeGroup.name)
    )
    return list(result.scalars().all())


async def get_envelope_group_by_id(
    session: AsyncSession, budget_id: UUID, envelope_group_id: UUID
) -> EnvelopeGroup:
    """Get an envelope group by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(EnvelopeGroup).where(
            EnvelopeGroup.id == envelope_group_id, EnvelopeGroup.budget_id == budget_id
        )
    )
    envelope_group = result.scalar_one_or_none()
    if not envelope_group:
        raise EnvelopeGroupNotFoundError(envelope_group_id)
    return envelope_group


async def create_envelope_group(
    session: AsyncSession, budget_id: UUID, envelope_group_in: EnvelopeGroupCreate
) -> EnvelopeGroup:
    """Create a new envelope group for a budget."""
    envelope_group = EnvelopeGroup(
        budget_id=budget_id,
        name=envelope_group_in.name,
        icon=envelope_group_in.icon,
        sort_order=envelope_group_in.sort_order,
    )
    session.add(envelope_group)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_envelope_group_name" in str(e):
            raise DuplicateEnvelopeGroupNameError(envelope_group_in.name) from e
        raise
    return envelope_group


async def update_envelope_group(
    session: AsyncSession,
    budget_id: UUID,
    envelope_group_id: UUID,
    envelope_group_in: EnvelopeGroupUpdate,
) -> EnvelopeGroup:
    """Update an existing envelope group."""
    envelope_group = await get_envelope_group_by_id(
        session, budget_id, envelope_group_id
    )

    update_data = envelope_group_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(envelope_group, field, value)

    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_envelope_group_name" in str(e):
            raise DuplicateEnvelopeGroupNameError(
                envelope_group_in.name or envelope_group.name
            ) from e
        raise
    return envelope_group


async def delete_envelope_group(
    session: AsyncSession, budget_id: UUID, envelope_group_id: UUID
) -> None:
    """Delete an envelope group."""
    envelope_group = await get_envelope_group_by_id(
        session, budget_id, envelope_group_id
    )
    await session.delete(envelope_group)
    await session.flush()
