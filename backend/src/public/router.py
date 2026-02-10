from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin import service as admin_service
from src.admin.schemas import RegistrationStatusResponse
from src.database import get_async_session

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/registration-status", response_model=RegistrationStatusResponse)
async def get_registration_status(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RegistrationStatusResponse:
    """Check if registration is enabled (public endpoint, no auth required)."""
    enabled = await admin_service.is_registration_enabled(session)
    return RegistrationStatusResponse(registration_enabled=enabled)
