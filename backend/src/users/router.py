from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_active_user
from src.database import get_async_session
from src.exceptions import UnauthorizedError
from src.rate_limit import limiter
from src.start_fresh import service as start_fresh_service
from src.start_fresh.schemas import (
    DataCategory,
    StartFreshPreview,
    StartFreshRequest,
    StartFreshResponse,
)
from src.users import service
from src.users.models import User
from src.users.schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[User, Depends(get_current_active_user)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_user(
    request: Request,  # noqa: ARG001 - required by slowapi limiter
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    return await service.create_user(session, user_in)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: CurrentUser,
) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    current_user: CurrentUser,
    user_in: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    return await service.update_user(session, current_user, user_in)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await service.delete_user(session, current_user)


@router.get("/me/delete-all-data/preview", response_model=StartFreshPreview)
async def preview_all_user_data_deletion(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    categories: Annotated[list[DataCategory], Query(...)],
) -> StartFreshPreview:
    """Preview what data will be deleted across all teams the user owns.

    Returns aggregated counts for each data type that would be affected.
    Use this before calling the delete endpoint to show users what will be removed.
    """
    return await start_fresh_service.get_all_user_data_preview(
        session, current_user.id, categories
    )


@router.post("/me/delete-all-data", response_model=StartFreshResponse)
async def delete_all_user_data(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: StartFreshRequest,
) -> StartFreshResponse:
    """Delete data from all teams the user owns.

    This is a destructive operation that cannot be undone.
    Requires the user's password for confirmation.

    Note: This only deletes data (transactions, accounts, etc.), not the teams
    themselves. Teams will be emptied but still exist.
    """
    # Verify password
    if not service.verify_password(request.password, current_user.hashed_password):
        raise UnauthorizedError("Invalid password")

    # Perform deletion across all owned teams
    deleted = await start_fresh_service.delete_all_user_data(
        session, current_user.id, request.categories
    )

    return StartFreshResponse(
        success=True,
        deleted=deleted,
        message="Data deleted successfully from all owned teams",
    )
