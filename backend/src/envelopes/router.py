from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.envelopes import service
from src.envelopes.models import Envelope
from src.envelopes.schemas import (
    EnvelopeActivityResponse,
    EnvelopeBalanceCorrectionResponse,
    EnvelopeBudgetSummaryResponse,
    EnvelopeCreate,
    EnvelopeResponse,
    EnvelopeSummaryResponse,
    EnvelopeUpdate,
)

router = APIRouter(prefix="/budgets/{budget_id}/envelopes", tags=["envelopes"])


def _envelope_to_response(envelope: Envelope) -> EnvelopeResponse:
    """Build EnvelopeResponse from an Envelope model."""
    # Get all database columns plus the computed created_at property
    data = {c.name: getattr(envelope, c.name) for c in envelope.__table__.columns}
    data["created_at"] = envelope.created_at  # Property computed from UUID7
    return EnvelopeResponse(**data)


@router.get(
    "",
    response_model=list[EnvelopeResponse],
)
async def list_envelopes(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[EnvelopeResponse]:
    envelopes = await service.list_envelopes(session, ctx.budget.id)
    return [_envelope_to_response(envelope) for envelope in envelopes]


@router.post(
    "",
    response_model=EnvelopeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_envelope(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_CREATE])
    ],
    envelope_in: EnvelopeCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeResponse:
    envelope = await service.create_envelope(session, ctx.budget.id, envelope_in)
    return _envelope_to_response(envelope)


@router.post(
    "/recalculate-balances",
    response_model=list[EnvelopeBalanceCorrectionResponse],
)
async def recalculate_balances(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.DATA_REPAIR])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[EnvelopeBalanceCorrectionResponse]:
    """Recalculate all envelope balances from allocations.

    Use this to fix envelope balances that have drifted from their allocations.
    Requires owner permissions (data:repair scope).
    """
    corrections = await service.recalculate_envelope_balances(session, ctx.budget.id)
    return [EnvelopeBalanceCorrectionResponse(**c) for c in corrections]


@router.get(
    "/summary",
    response_model=EnvelopeSummaryResponse,
)
async def get_envelope_summary(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeSummaryResponse:
    """Get financial summary including Ready to Assign and unfunded CC debt."""
    ready_to_assign = await service.calculate_unallocated_balance(
        session, ctx.budget.id
    )
    unfunded_cc_debt = await service.calculate_unfunded_cc_debt(session, ctx.budget.id)
    return EnvelopeSummaryResponse(
        ready_to_assign=ready_to_assign,
        unfunded_cc_debt=unfunded_cc_debt,
    )


@router.get(
    "/budget-summary",
    response_model=EnvelopeBudgetSummaryResponse,
)
async def get_envelope_budget_summary(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[
        date, Query(description="Start date for filtering (inclusive)")
    ],
    end_date: Annotated[date, Query(description="End date for filtering (inclusive)")],
) -> EnvelopeBudgetSummaryResponse:
    """Get budget summary with date-filtered allocated/activity amounts.

    Returns all envelopes grouped by envelope group, with:
    - allocated: Sum of transfers in the date range
    - activity: Sum of transaction-based allocations in the date range
    - balance: Current envelope balance (not date-filtered)
    """
    summary = await service.get_envelope_budget_summary(
        session, ctx.budget.id, start_date, end_date
    )
    return EnvelopeBudgetSummaryResponse(**summary)


@router.get(
    "/{envelope_id}",
    response_model=EnvelopeResponse,
)
async def get_envelope(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_READ])
    ],
    envelope_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeResponse:
    envelope = await service.get_envelope_by_id(session, ctx.budget.id, envelope_id)
    return _envelope_to_response(envelope)


@router.patch(
    "/{envelope_id}",
    response_model=EnvelopeResponse,
)
async def update_envelope(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_UPDATE])
    ],
    envelope_id: UUID,
    envelope_in: EnvelopeUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeResponse:
    envelope = await service.update_envelope(
        session, ctx.budget.id, envelope_id, envelope_in
    )
    return _envelope_to_response(envelope)


@router.delete(
    "/{envelope_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_envelope(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_DELETE])
    ],
    envelope_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_envelope(session, ctx.budget.id, envelope_id)


@router.get(
    "/{envelope_id}/activity",
    response_model=EnvelopeActivityResponse,
)
async def get_envelope_activity(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.ENVELOPES_READ])
    ],
    envelope_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[
        date, Query(description="Start date for filtering (inclusive)")
    ],
    end_date: Annotated[date, Query(description="End date for filtering (inclusive)")],
) -> EnvelopeActivityResponse:
    """Get activity details for an envelope in a date range.

    Returns transaction-based allocations with account/payee information.
    """
    activity = await service.get_envelope_activity(
        session, ctx.budget.id, envelope_id, start_date, end_date
    )
    return EnvelopeActivityResponse(**activity)
