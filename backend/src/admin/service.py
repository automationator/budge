from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models import SystemSettings
from src.admin.schemas import SystemSettingsUpdate


async def get_system_settings(session: AsyncSession) -> SystemSettings:
    """Get the system settings (single row)."""
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        # Create default settings if they don't exist (shouldn't happen after migration)
        settings = SystemSettings(id=1, registration_enabled=True)
        session.add(settings)
        await session.flush()
    return settings


async def update_system_settings(
    session: AsyncSession,
    settings_in: SystemSettingsUpdate,
) -> SystemSettings:
    """Update system settings."""
    settings = await get_system_settings(session)
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    await session.flush()
    return settings


async def is_registration_enabled(session: AsyncSession) -> bool:
    """Check if registration is enabled."""
    settings = await get_system_settings(session)
    return settings.registration_enabled
