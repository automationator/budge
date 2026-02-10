"""Seed the database with required initial data.

Run after migrations to ensure the database has all required rows.
All operations are idempotent (safe to run multiple times).
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.admin.models import SystemSettings
from src.config import settings


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session, session.begin():
        # Ensure the system_settings singleton row exists
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.id == 1)
        )
        if result.scalar_one_or_none() is None:
            session.add(SystemSettings(id=1, registration_enabled=True))
            print("Seeded system_settings row")
        else:
            print("system_settings row already exists")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
