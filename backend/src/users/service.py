from uuid import UUID

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.users.exceptions import (
    RegistrationDisabledError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError(user_id)
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def _is_first_user(session: AsyncSession) -> bool:
    """Check if there are no users in the database."""
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar()
    return count == 0


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
    *,
    skip_registration_check: bool = False,
) -> User:
    """Create a new user.

    Args:
        session: Database session
        user_in: User creation data
        skip_registration_check: If True, skip the registration enabled check.
            Used for E2E testing to create users when registration is disabled.
    """
    # Check if registration is enabled (skip for first user or if explicitly skipped)
    is_first = await _is_first_user(session)
    if not skip_registration_check and not is_first:
        from src.admin.service import is_registration_enabled

        if not await is_registration_enabled(session):
            raise RegistrationDisabledError()

    existing_username = await get_user_by_username(session, user_in.username)
    if existing_username:
        raise UsernameAlreadyExistsError(user_in.username)

    # First user becomes admin
    user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
        is_admin=is_first,
    )
    session.add(user)
    await session.flush()

    # Create a default budget for the user
    budget = Budget(name=f"{user_in.username}'s Budget", owner_id=user.id)
    session.add(budget)
    await session.flush()

    # Add the owner as a member of their budget with owner role
    user_budget = BudgetMembership(
        user_id=user.id, budget_id=budget.id, role=BudgetRole.OWNER
    )
    session.add(user_budget)
    await session.flush()

    return user


async def update_user(
    session: AsyncSession,
    user: User,
    user_in: UserUpdate,
) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await session.flush()
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.flush()
