from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_active_user
from src.budgets import service
from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.exceptions import UserNotBudgetMemberError
from src.budgets.schemas import (
    AddMemberRequest,
    BudgetMemberWithRoleResponse,
    BudgetResponse,
    CreateBudgetRequest,
    DeleteBudgetRequest,
    MemberRequest,
    MemberRoleUpdate,
    MemberScopesResponse,
    ScopeModification,
    UpdateBudgetRequest,
)
from src.budgets.scopes import ROLE_SCOPES, BudgetScope, get_effective_scopes
from src.database import get_async_session
from src.exceptions import UnauthorizedError
from src.pagination import CursorPage
from src.users.models import User
from src.users.service import get_user_by_id, verify_password

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=CursorPage[BudgetResponse])
async def list_my_budgets(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CursorPage[BudgetResponse]:
    """List all budgets the current user is a member of."""
    budgets = await service.get_budgets_for_user(session, user.id)
    return CursorPage(
        items=[BudgetResponse.model_validate(budget) for budget in budgets],
        next_cursor=None,
        has_more=False,
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: CreateBudgetRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BudgetResponse:
    """Create a new budget with the current user as owner."""
    budget = await service.create_budget(session, budget_in.name, user.id)
    return BudgetResponse.model_validate(budget)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.BUDGET_UPDATE])
    ],
    budget_in: UpdateBudgetRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BudgetResponse:
    """Update a budget's settings. Requires budget:update scope."""
    budget = await service.update_budget(session, ctx.budget, budget_in)
    return BudgetResponse.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.BUDGET_DELETE])
    ],
    request: DeleteBudgetRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Delete a budget and all its data.

    This is a destructive operation that cannot be undone.
    Requires the user's password for confirmation and budget:delete scope (owner only).
    """
    # Verify password
    user = await get_user_by_id(session, ctx.user.id)
    if not verify_password(request.password, user.hashed_password):
        raise UnauthorizedError("Invalid password")

    await service.delete_budget(session, ctx.budget.id)


@router.get(
    "/{budget_id}/members",
    response_model=list[BudgetMemberWithRoleResponse],
)
async def list_members(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_READ])
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[dict]:
    members = await service.list_budget_members(session, ctx.budget.id)
    return [
        {
            "id": member.user.id,
            "username": member.user.username,
            "role": member.role,
            "effective_scopes": list(
                get_effective_scopes(
                    member.role, member.scope_additions, member.scope_removals
                )
            ),
        }
        for member in members
    ]


@router.post(
    "/{budget_id}/members",
    response_model=BudgetMemberWithRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_ADD])
    ],
    member_in: AddMemberRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    user, membership = await service.add_member_to_budget(
        session,
        ctx.budget.id,
        MemberRequest(username=member_in.username),
        member_in.role,
    )
    effective_scopes = get_effective_scopes(
        membership.role, membership.scope_additions, membership.scope_removals
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": membership.role,
        "effective_scopes": list(effective_scopes),
    }


@router.delete("/{budget_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_REMOVE])
    ],
    member_in: MemberRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.remove_member_from_budget(session, ctx, member_in)


@router.patch(
    "/{budget_id}/members/{user_id}/role",
    response_model=BudgetMemberWithRoleResponse,
)
async def update_member_role(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_MANAGE_ROLES]),
    ],
    user_id: UUID,
    role_update: MemberRoleUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    membership = await service.update_member_role(
        session, ctx, user_id, role_update.role
    )
    # Get the user info
    user = await get_user_by_id(session, user_id)
    effective_scopes = get_effective_scopes(
        membership.role, membership.scope_additions, membership.scope_removals
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": membership.role,
        "effective_scopes": list(effective_scopes),
    }


@router.get(
    "/{budget_id}/members/{user_id}/scopes",
    response_model=MemberScopesResponse,
)
async def get_member_scopes(
    ctx: Annotated[
        BudgetContext, Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_READ])
    ],
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    membership = await service.get_membership(session, ctx.budget.id, user_id)
    if not membership:
        raise UserNotBudgetMemberError(str(user_id))

    role_scopes = [s.value for s in ROLE_SCOPES.get(membership.role, set())]
    effective_scopes = get_effective_scopes(
        membership.role, membership.scope_additions, membership.scope_removals
    )
    return {
        "user_id": user_id,
        "role": membership.role,
        "role_scopes": role_scopes,
        "scope_additions": membership.scope_additions,
        "scope_removals": membership.scope_removals,
        "effective_scopes": list(effective_scopes),
    }


@router.post(
    "/{budget_id}/members/{user_id}/scopes",
    response_model=MemberScopesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member_scope(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_MANAGE_ROLES]),
    ],
    user_id: UUID,
    scope_mod: ScopeModification,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    membership = await service.add_member_scope(session, ctx, user_id, scope_mod.scope)
    role_scopes = [s.value for s in ROLE_SCOPES.get(membership.role, set())]
    effective_scopes = get_effective_scopes(
        membership.role, membership.scope_additions, membership.scope_removals
    )
    return {
        "user_id": user_id,
        "role": membership.role,
        "role_scopes": role_scopes,
        "scope_additions": membership.scope_additions,
        "scope_removals": membership.scope_removals,
        "effective_scopes": list(effective_scopes),
    }


@router.delete(
    "/{budget_id}/members/{user_id}/scopes",
    response_model=MemberScopesResponse,
)
async def remove_member_scope(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.MEMBERS_MANAGE_ROLES]),
    ],
    user_id: UUID,
    scope_mod: ScopeModification,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    membership = await service.remove_member_scope(
        session, ctx, user_id, scope_mod.scope
    )
    role_scopes = [s.value for s in ROLE_SCOPES.get(membership.role, set())]
    effective_scopes = get_effective_scopes(
        membership.role, membership.scope_additions, membership.scope_removals
    )
    return {
        "user_id": user_id,
        "role": membership.role,
        "role_scopes": role_scopes,
        "scope_additions": membership.scope_additions,
        "scope_removals": membership.scope_removals,
        "effective_scopes": list(effective_scopes),
    }
