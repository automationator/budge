from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import Account
from src.allocation_rules.models import AllocationRule
from src.allocations.models import Allocation
from src.budgets.dependencies import BudgetContext
from src.budgets.exceptions import (
    BudgetNotFoundError,
    CannotAssignOwnerRoleError,
    CannotModifyOwnerRoleError,
    CannotRemoveBudgetOwnerError,
    InsufficientPermissionsError,
    UserAlreadyBudgetMemberError,
    UserNotBudgetMemberError,
)
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.budgets.schemas import MemberRequest, UpdateBudgetRequest
from src.budgets.scopes import ROLE_SCOPES, get_effective_scopes
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.locations.models import Location
from src.payees.models import Payee
from src.recurring_transactions.models import RecurringTransaction
from src.transactions.models import Transaction
from src.users.exceptions import UserNotFoundError
from src.users.models import User


async def create_budget(
    session: AsyncSession,
    name: str,
    owner_id: UUID,
) -> Budget:
    """Create a new budget with the given user as owner."""
    budget = Budget(name=name, owner_id=owner_id)
    session.add(budget)
    await session.flush()

    # Create membership for the owner
    membership = BudgetMembership(
        user_id=owner_id,
        budget_id=budget.id,
        role=BudgetRole.OWNER,
    )
    session.add(membership)
    await session.flush()

    return budget


async def get_budget_by_id(session: AsyncSession, budget_id: UUID) -> Budget:
    result = await session.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise BudgetNotFoundError(budget_id)
    return budget


async def get_budgets_for_user(session: AsyncSession, user_id: UUID) -> list[Budget]:
    """Get all budgets that a user is a member of."""
    result = await session.execute(
        select(Budget)
        .join(BudgetMembership, BudgetMembership.budget_id == Budget.id)
        .where(BudgetMembership.user_id == user_id)
        .order_by(Budget.name)
    )
    return list(result.scalars().all())


async def list_budget_members(
    session: AsyncSession,
    budget_id: UUID,
) -> list[BudgetMembership]:
    """List all members of a budget with their user info."""
    result = await session.execute(
        select(BudgetMembership)
        .where(BudgetMembership.budget_id == budget_id)
        .options(selectinload(BudgetMembership.user))
    )
    return list(result.scalars().all())


async def get_membership(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
) -> BudgetMembership | None:
    """Get a user's membership in a budget."""
    result = await session.execute(
        select(BudgetMembership).where(
            BudgetMembership.budget_id == budget_id,
            BudgetMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def add_member_to_budget(
    session: AsyncSession,
    budget_id: UUID,
    member_in: MemberRequest,
    role: BudgetRole = BudgetRole.MEMBER,
) -> tuple[User, BudgetMembership]:
    """Add a member to a budget with the specified role."""
    # Find the user to add by username
    result = await session.execute(
        select(User).where(User.username == member_in.username)
    )

    user_to_add = result.scalar_one_or_none()
    if not user_to_add:
        raise UserNotFoundError()

    # Check if user is already a member
    existing_membership = await get_membership(session, budget_id, user_to_add.id)
    if existing_membership:
        raise UserAlreadyBudgetMemberError(user_to_add.username)

    # Cannot assign owner role directly
    if role == BudgetRole.OWNER:
        raise CannotAssignOwnerRoleError()

    # Add the user to the budget
    membership = BudgetMembership(
        user_id=user_to_add.id, budget_id=budget_id, role=role
    )
    session.add(membership)
    await session.flush()

    return user_to_add, membership


async def remove_member_from_budget(
    session: AsyncSession,
    budget_ctx: BudgetContext,
    member_in: MemberRequest,
) -> None:
    """Remove a member from a budget. Authorization is handled by BudgetContext."""
    # Find the user by username
    result = await session.execute(
        select(User).where(User.username == member_in.username)
    )

    user_to_remove = result.scalar_one_or_none()
    if not user_to_remove:
        raise UserNotFoundError()

    # Cannot remove the owner from their own budget
    if user_to_remove.id == budget_ctx.budget.owner_id:
        raise CannotRemoveBudgetOwnerError()

    # Find the membership
    membership = await get_membership(session, budget_ctx.budget.id, user_to_remove.id)
    if not membership:
        raise UserNotBudgetMemberError(member_in.username)

    await session.delete(membership)
    await session.flush()


async def update_member_role(
    session: AsyncSession,
    budget_ctx: BudgetContext,
    target_user_id: UUID,
    new_role: BudgetRole,
) -> BudgetMembership:
    """Update a member's role. Clears scope overrides when role changes."""
    # Cannot assign owner role
    if new_role == BudgetRole.OWNER:
        raise CannotAssignOwnerRoleError()

    # Cannot change owner's role
    if target_user_id == budget_ctx.budget.owner_id:
        raise CannotModifyOwnerRoleError()

    membership = await get_membership(session, budget_ctx.budget.id, target_user_id)
    if not membership:
        raise UserNotBudgetMemberError(str(target_user_id))

    membership.role = new_role
    # Clear overrides when role changes
    membership.scope_additions = []
    membership.scope_removals = []

    await session.flush()
    return membership


async def add_member_scope(
    session: AsyncSession,
    budget_ctx: BudgetContext,
    target_user_id: UUID,
    scope: str,
) -> BudgetMembership:
    """Add a scope to a member beyond their role defaults."""
    # Validate actor has the scope they're granting
    if scope not in budget_ctx.effective_scopes:
        raise InsufficientPermissionsError([scope])

    membership = await get_membership(session, budget_ctx.budget.id, target_user_id)
    if not membership:
        raise UserNotBudgetMemberError(str(target_user_id))

    # Add scope if not already present
    if scope not in membership.scope_additions:
        membership.scope_additions = [*membership.scope_additions, scope]

    # Remove from removals if present
    if scope in membership.scope_removals:
        membership.scope_removals = [s for s in membership.scope_removals if s != scope]

    await session.flush()
    return membership


async def remove_member_scope(
    session: AsyncSession,
    budget_ctx: BudgetContext,
    target_user_id: UUID,
    scope: str,
) -> BudgetMembership:
    """Remove a scope from a member."""
    membership = await get_membership(session, budget_ctx.budget.id, target_user_id)
    if not membership:
        raise UserNotBudgetMemberError(str(target_user_id))

    role_default_scopes = {s.value for s in ROLE_SCOPES.get(membership.role, set())}

    # If scope is in additions, remove from additions
    if scope in membership.scope_additions:
        membership.scope_additions = [
            s for s in membership.scope_additions if s != scope
        ]
    # If scope is a role default, add to removals
    elif scope in role_default_scopes and scope not in membership.scope_removals:
        membership.scope_removals = [*membership.scope_removals, scope]

    await session.flush()
    return membership


async def get_member_effective_scopes(
    session: AsyncSession,
    budget_id: UUID,
    user_id: UUID,
) -> set[str]:
    """Get the effective scopes for a user in a budget."""
    membership = await get_membership(session, budget_id, user_id)
    if not membership:
        return set()

    return get_effective_scopes(
        membership.role,
        membership.scope_additions,
        membership.scope_removals,
    )


async def update_budget(
    session: AsyncSession,
    budget: Budget,
    budget_in: UpdateBudgetRequest,
) -> Budget:
    """Update a budget's settings."""
    update_data = budget_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(budget, field, value)
    await session.flush()
    return budget


async def delete_budget(
    session: AsyncSession,
    budget_id: UUID,
) -> dict[str, int]:
    """Delete a budget and all its associated data.

    Deletes data in correct order respecting FK constraints:
    1. Allocations
    2. Transactions
    3. Recurring transactions
    4. Allocation rules
    5. Locations
    6. Payees
    7. Envelopes
    8. Envelope groups
    9. Accounts
    10. Budget memberships
    11. Budget

    Returns counts of what was deleted.
    """
    deleted: dict[str, int] = {}

    # 1. Delete allocations (references transactions and envelopes)
    result = await session.execute(
        delete(Allocation)
        .where(Allocation.budget_id == budget_id)
        .returning(Allocation.id)
    )
    deleted["allocations"] = len(result.all())

    # 2. Delete transactions (references accounts, payees, locations)
    result = await session.execute(
        delete(Transaction)
        .where(Transaction.budget_id == budget_id)
        .returning(Transaction.id)
    )
    deleted["transactions"] = len(result.all())

    # 3. Delete recurring transactions
    result = await session.execute(
        delete(RecurringTransaction)
        .where(RecurringTransaction.budget_id == budget_id)
        .returning(RecurringTransaction.id)
    )
    deleted["recurring_transactions"] = len(result.all())

    # 4. Delete allocation rules (references envelopes)
    result = await session.execute(
        delete(AllocationRule)
        .where(AllocationRule.budget_id == budget_id)
        .returning(AllocationRule.id)
    )
    deleted["allocation_rules"] = len(result.all())

    # 5. Delete locations
    result = await session.execute(
        delete(Location).where(Location.budget_id == budget_id).returning(Location.id)
    )
    deleted["locations"] = len(result.all())

    # 6. Delete payees
    result = await session.execute(
        delete(Payee).where(Payee.budget_id == budget_id).returning(Payee.id)
    )
    deleted["payees"] = len(result.all())

    # 7. Delete envelopes
    result = await session.execute(
        delete(Envelope).where(Envelope.budget_id == budget_id).returning(Envelope.id)
    )
    deleted["envelopes"] = len(result.all())

    # 8. Delete envelope groups
    result = await session.execute(
        delete(EnvelopeGroup)
        .where(EnvelopeGroup.budget_id == budget_id)
        .returning(EnvelopeGroup.id)
    )
    deleted["envelope_groups"] = len(result.all())

    # 9. Delete accounts (must be after transactions)
    result = await session.execute(
        delete(Account).where(Account.budget_id == budget_id).returning(Account.id)
    )
    deleted["accounts"] = len(result.all())

    # 10. Delete budget memberships
    result = await session.execute(
        delete(BudgetMembership)
        .where(BudgetMembership.budget_id == budget_id)
        .returning(BudgetMembership.id)
    )
    deleted["memberships"] = len(result.all())

    # 11. Delete the budget itself
    result = await session.execute(
        delete(Budget).where(Budget.id == budget_id).returning(Budget.id)
    )
    deleted["budgets"] = len(result.all())

    await session.flush()
    return deleted
