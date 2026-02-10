from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.allocation_rules import service
from src.allocation_rules.schemas import (
    AllocationRuleCreate,
    AllocationRuleResponse,
    AllocationRuleUpdate,
    ApplyRulesResponse,
    RulePreviewInput,
    RulePreviewResponse,
)
from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session

router = APIRouter(
    prefix="/budgets/{budget_id}/allocation-rules", tags=["allocation-rules"]
)


@router.get(
    "",
    response_model=list[AllocationRuleResponse],
)
async def list_rules(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    active_only: Annotated[bool, Query()] = False,
) -> list[AllocationRuleResponse]:
    """List all allocation rules for the budget."""
    rules = await service.list_rules(session, ctx.budget.id, active_only=active_only)
    return [AllocationRuleResponse.model_validate(r) for r in rules]


@router.get(
    "/{rule_id}",
    response_model=AllocationRuleResponse,
)
async def get_rule(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_READ]),
    ],
    rule_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationRuleResponse:
    """Get a single allocation rule."""
    rule = await service.get_rule_by_id(session, ctx.budget.id, rule_id)
    return AllocationRuleResponse.model_validate(rule)


@router.post(
    "",
    response_model=AllocationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_CREATE]),
    ],
    rule_in: AllocationRuleCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationRuleResponse:
    """Create a new allocation rule."""
    rule = await service.create_rule(session, ctx.budget.id, rule_in)
    return AllocationRuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=AllocationRuleResponse,
)
async def update_rule(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_UPDATE]),
    ],
    rule_id: UUID,
    rule_in: AllocationRuleUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationRuleResponse:
    """Update an allocation rule."""
    rule = await service.update_rule(session, ctx.budget.id, rule_id, rule_in)
    return AllocationRuleResponse.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rule(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_DELETE]),
    ],
    rule_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Delete an allocation rule."""
    await service.delete_rule(session, ctx.budget.id, rule_id)


@router.post(
    "/preview",
    response_model=RulePreviewResponse,
)
async def preview_rules(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATION_RULES_READ]),
    ],
    preview_in: RulePreviewInput,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RulePreviewResponse:
    """Preview how rules would distribute a given income amount.

    This is a dry run - no allocations are created.
    """
    allocations, unallocated = await service.preview_rules(
        session, ctx.budget.id, preview_in.amount
    )
    return RulePreviewResponse(
        income_amount=preview_in.amount,
        allocations=allocations,
        unallocated=unallocated,
    )


@router.post(
    "/apply",
    response_model=ApplyRulesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_rules(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.ALLOCATIONS_CREATE]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ApplyRulesResponse:
    """Apply allocation rules to distribute the current unallocated balance.

    Takes money from the unallocated envelope and distributes it according
    to active allocation rules. Use the preview endpoint first to see
    what allocations would be created.
    """
    initial, allocations, final = await service.apply_rules_to_unallocated(
        session, ctx.budget.id
    )
    return ApplyRulesResponse(
        initial_unallocated=initial,
        allocations=allocations,
        final_unallocated=final,
    )
