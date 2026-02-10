from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path
from fastapi.security import SecurityScopes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_active_user
from src.budgets.exceptions import (
    BudgetNotFoundError,
    InsufficientPermissionsError,
    NotBudgetMemberError,
)
from src.budgets.models import Budget, BudgetMembership
from src.budgets.scopes import get_effective_scopes
from src.database import get_async_session
from src.users.models import User


@dataclass
class BudgetContext:
    """Context object containing budget, membership, and effective scopes."""

    budget: Budget
    membership: BudgetMembership
    user: User
    effective_scopes: set[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.effective_scopes

    def has_any_scope(self, *scopes: str) -> bool:
        return bool(self.effective_scopes & set(scopes))

    def has_all_scopes(self, *scopes: str) -> bool:
        return set(scopes).issubset(self.effective_scopes)

    @property
    def is_owner(self) -> bool:
        return self.budget.owner_id == self.user.id


class BudgetSecurity:
    """
    Factory class for creating budget-scoped security dependencies.

    Usage in routes:
        @router.get("/{budget_id}/members")
        async def list_members(
            ctx: Annotated[
                BudgetContext,
                Security(BudgetSecurity(), scopes=["members:read"])
            ],
        ) -> list[Member]:
            ...
    """

    async def __call__(
        self,
        security_scopes: SecurityScopes,
        budget_id: Annotated[UUID, Path()],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_async_session)],
    ) -> BudgetContext:
        # Fetch budget
        result = await session.execute(select(Budget).where(Budget.id == budget_id))
        budget = result.scalar_one_or_none()
        if not budget:
            raise BudgetNotFoundError(budget_id)

        # Fetch membership
        result = await session.execute(
            select(BudgetMembership).where(
                BudgetMembership.budget_id == budget_id,
                BudgetMembership.user_id == current_user.id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise NotBudgetMemberError()

        # Calculate effective scopes
        effective_scopes = get_effective_scopes(
            membership.role,
            membership.scope_additions,
            membership.scope_removals,
        )

        # Check required scopes
        if security_scopes.scopes:
            missing_scopes = set(security_scopes.scopes) - effective_scopes
            if missing_scopes:
                raise InsufficientPermissionsError(list(missing_scopes))

        return BudgetContext(
            budget=budget,
            membership=membership,
            user=current_user,
            effective_scopes=effective_scopes,
        )
