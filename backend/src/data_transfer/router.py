"""Router for data export/import endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.data_transfer import service
from src.data_transfer.schemas import ExportResponse, ImportRequest, ImportResult
from src.database import get_async_session
from src.exceptions import UnauthorizedError
from src.users.service import get_user_by_id, verify_password

router = APIRouter(prefix="/budgets/{budget_id}", tags=["data-transfer"])


@router.get(
    "/export",
    response_model=ExportResponse,
)
async def export_budget_data(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.DATA_EXPORT])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ExportResponse:
    """Export all budget data as JSON.

    Returns a versioned JSON export containing all budget-owned data:
    accounts, envelopes, transactions, allocations, payees, locations,
    recurring transactions, and allocation rules.

    This can be used for backup or migration purposes.
    """
    data = await service.export_budget_data(session, ctx.budget.id)
    return ExportResponse(data=data)


@router.post(
    "/import",
    response_model=ImportResult,
)
async def import_budget_data(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.DATA_IMPORT])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: ImportRequest,
) -> ImportResult:
    """Import budget data from JSON export.

    Imports data from a previous export, generating new UUIDs while
    maintaining all relationships between entities.

    Args:
        request: Import request containing:
            - data: The exported data to import
            - clear_existing: If true, delete all existing budget data before import
            - password: User's password for confirmation

    Returns:
        Import result with counts of imported entities and any errors.

    Note: Import is atomic - if any part fails, no data is imported.
    User associations (user_id on transactions) are not preserved.
    """
    # Verify password
    user = await get_user_by_id(session, ctx.user.id)
    if not verify_password(request.password, user.hashed_password):
        raise UnauthorizedError("Invalid password")

    result = await service.import_budget_data(
        session,
        ctx.budget.id,
        request.data,
        clear_existing=request.clear_existing,
    )
    return result
