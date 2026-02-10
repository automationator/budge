from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.payees.exceptions import (
    DuplicatePayeeNameError,
    PayeeInUseError,
    PayeeNotFoundError,
)
from src.payees.models import Payee
from src.payees.schemas import PayeeCreate, PayeeUpdate


async def list_payees(session: AsyncSession, budget_id: UUID) -> list[Payee]:
    """List all payees for a budget, ordered by name."""
    result = await session.execute(
        select(Payee).where(Payee.budget_id == budget_id).order_by(Payee.name)
    )
    return list(result.scalars().all())


async def get_payee_by_id(
    session: AsyncSession, budget_id: UUID, payee_id: UUID
) -> Payee:
    """Get a payee by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Payee).where(Payee.id == payee_id, Payee.budget_id == budget_id)
    )
    payee = result.scalar_one_or_none()
    if not payee:
        raise PayeeNotFoundError(payee_id)
    return payee


async def create_payee(
    session: AsyncSession, budget_id: UUID, payee_in: PayeeCreate
) -> Payee:
    """Create a new payee for a budget."""
    payee = Payee(
        budget_id=budget_id,
        name=payee_in.name,
        icon=payee_in.icon,
        description=payee_in.description,
    )
    session.add(payee)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_payee_name" in str(e):
            raise DuplicatePayeeNameError(payee_in.name) from e
        raise
    return payee


async def update_payee(
    session: AsyncSession, budget_id: UUID, payee_id: UUID, payee_in: PayeeUpdate
) -> Payee:
    """Update an existing payee."""
    payee = await get_payee_by_id(session, budget_id, payee_id)

    update_data = payee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payee, field, value)

    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_payee_name" in str(e):
            raise DuplicatePayeeNameError(payee_in.name or payee.name) from e
        raise
    return payee


async def delete_payee(session: AsyncSession, budget_id: UUID, payee_id: UUID) -> None:
    """Delete a payee.

    Raises:
        PayeeNotFoundError: If the payee doesn't exist
        PayeeInUseError: If the payee is linked to existing transactions
    """
    payee = await get_payee_by_id(session, budget_id, payee_id)
    payee_name = payee.name
    await session.delete(payee)
    try:
        await session.flush()
    except IntegrityError as e:
        # Check if this is a foreign key violation from transactions
        # The session will be rolled back by the framework when we raise
        if "payees" in str(e) or "fk_" in str(e).lower():
            raise PayeeInUseError(payee_name) from e
        raise


async def get_default_envelope(
    session: AsyncSession,
    budget_id: UUID,
    payee_id: UUID,
) -> UUID | None:
    """Get the default envelope for a payee.

    Args:
        session: Database session
        budget_id: Budget ID
        payee_id: Payee ID

    Returns:
        Default envelope ID, or None if not set
    """
    payee = await get_payee_by_id(session, budget_id, payee_id)
    return payee.default_envelope_id


async def set_default_envelope_if_unset(
    session: AsyncSession,
    budget_id: UUID,
    payee_id: UUID,
    envelope_id: UUID,
) -> None:
    """Set the default envelope for a payee if not already set.

    Called when creating the first transaction with a payee+envelope.

    Args:
        session: Database session
        budget_id: Budget ID
        payee_id: Payee ID
        envelope_id: Envelope ID to set as default
    """
    payee = await get_payee_by_id(session, budget_id, payee_id)
    if payee.default_envelope_id is None:
        payee.default_envelope_id = envelope_id
        await session.flush()
