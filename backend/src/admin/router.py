from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin import service
from src.admin.dependencies import require_admin
from src.admin.schemas import (
    SystemSettingsResponse,
    SystemSettingsUpdate,
    VersionResponse,
)
from src.database import get_async_session
from src.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=SystemSettingsResponse)
async def get_settings(
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SystemSettingsResponse:
    """Get system settings (admin only)."""
    settings = await service.get_system_settings(session)
    return SystemSettingsResponse.model_validate(settings)


@router.patch("/settings", response_model=SystemSettingsResponse)
async def update_settings(
    settings_in: SystemSettingsUpdate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SystemSettingsResponse:
    """Update system settings (admin only)."""
    settings = await service.update_system_settings(session, settings_in)
    return SystemSettingsResponse.model_validate(settings)


@router.get("/version", response_model=VersionResponse)
async def get_version(
    _admin: Annotated[User, Depends(require_admin)],
) -> VersionResponse:
    """Check for available updates (admin only)."""
    return await service.check_version()
