"""Router for Start Fresh endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.exceptions import UnauthorizedError
from src.start_fresh import service
from src.start_fresh.schemas import (
    DataCategory,
    StartFreshPreview,
    StartFreshRequest,
    StartFreshResponse,
)
from src.users.service import get_user_by_id, verify_password

router = APIRouter(prefix="/budgets/{budget_id}/start-fresh", tags=["start-fresh"])


@router.get(
    "/preview",
    response_model=StartFreshPreview,
)
async def preview_deletion(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.BUDGET_DELETE])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    categories: Annotated[list[DataCategory], Query(...)],
) -> StartFreshPreview:
    """Preview what data will be deleted.

    Returns counts for each data type that would be affected by the deletion.
    Use this before calling the delete endpoint to show users what will be removed.
    """
    return await service.get_deletion_preview(session, ctx.budget.id, categories)


@router.post(
    "",
    response_model=StartFreshResponse,
)
async def start_fresh(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.BUDGET_DELETE])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: StartFreshRequest,
) -> StartFreshResponse:
    """Delete selected budget data after password verification.

    This is a destructive operation that cannot be undone.
    Requires the user's password for confirmation.

    Categories:
    - all: Delete everything
    - transactions: Delete all transactions and their allocations
    - recurring: Delete recurring transactions
    - envelopes: Delete envelopes, envelope groups, and allocation rules
    - accounts: Delete accounts (cascades to transactions)
    - payees: Delete payees not linked to any transaction
    - locations: Delete locations
    """
    # Verify password
    user = await get_user_by_id(session, ctx.user.id)
    if not verify_password(request.password, user.hashed_password):
        raise UnauthorizedError("Invalid password")

    # Perform deletion
    deleted = await service.delete_budget_data(
        session, ctx.budget.id, request.categories
    )

    return StartFreshResponse(
        success=True,
        deleted=deleted,
        message="Data deleted successfully",
    )
