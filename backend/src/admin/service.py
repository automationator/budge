import logging
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models import SystemSettings
from src.admin.schemas import SystemSettingsUpdate, VersionResponse
from src.config import settings

logger = logging.getLogger(__name__)

# In-memory cache for version check
_version_cache: VersionResponse | None = None
_version_cache_time: float = 0.0
_VERSION_CACHE_TTL = 3600  # 1 hour


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
    db_settings = await get_system_settings(session)
    return db_settings.registration_enabled


def _is_newer(latest: str, current: str) -> bool:
    """Check if latest version is newer than current version."""
    try:
        latest_parts = [int(p) for p in latest.split(".")]
        current_parts = [int(p) for p in current.split(".")]
    except ValueError:
        return False

    # Pad shorter version with zeros
    max_len = max(len(latest_parts), len(current_parts))
    latest_parts.extend([0] * (max_len - len(latest_parts)))
    current_parts.extend([0] * (max_len - len(current_parts)))

    return latest_parts > current_parts


async def check_version() -> VersionResponse:
    """Check for available updates via GitHub API."""
    global _version_cache, _version_cache_time

    current = settings.app_version

    if current == "dev":
        return VersionResponse(
            current_version=current,
            error="Running development build",
        )

    # Return cached result if still fresh
    now = time.monotonic()
    if _version_cache is not None and (now - _version_cache_time) < _VERSION_CACHE_TTL:
        return _version_cache

    url = f"https://api.github.com/repos/{settings.github_repo}/releases/latest"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Accept": "application/vnd.github+json"},
            )

        if response.status_code == 200:
            data = response.json()
            latest = data.get("tag_name", "")
            release_url = data.get("html_url")
            result = VersionResponse(
                current_version=current,
                latest_version=latest,
                update_available=_is_newer(latest, current),
                release_url=release_url,
            )
        elif response.status_code == 404:
            result = VersionResponse(
                current_version=current,
                error="No releases found",
            )
        elif response.status_code == 403:
            # Rate limited — return stale cache if available
            if _version_cache is not None:
                return VersionResponse(
                    current_version=current,
                    latest_version=_version_cache.latest_version,
                    update_available=_version_cache.update_available,
                    release_url=_version_cache.release_url,
                    error="GitHub API rate limited, showing cached result",
                )
            result = VersionResponse(
                current_version=current,
                error="GitHub API rate limited",
            )
        else:
            result = VersionResponse(
                current_version=current,
                error=f"GitHub API returned status {response.status_code}",
            )
    except httpx.ConnectError:
        if _version_cache is not None:
            return VersionResponse(
                current_version=current,
                latest_version=_version_cache.latest_version,
                update_available=_version_cache.update_available,
                release_url=_version_cache.release_url,
                error="Could not connect to GitHub, showing cached result",
            )
        result = VersionResponse(
            current_version=current,
            error="Could not connect to GitHub",
        )
    except httpx.TimeoutException:
        if _version_cache is not None:
            return VersionResponse(
                current_version=current,
                latest_version=_version_cache.latest_version,
                update_available=_version_cache.update_available,
                release_url=_version_cache.release_url,
                error="GitHub API timed out, showing cached result",
            )
        result = VersionResponse(
            current_version=current,
            error="GitHub API timed out",
        )

    # Cache successful results (those with a latest_version)
    if result.latest_version is not None:
        _version_cache = result
        _version_cache_time = now

    return result
