from collections.abc import AsyncGenerator
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import settings

# Context variable for per-request schema (used in E2E tests)
e2e_schema_context: ContextVar[str | None] = ContextVar("e2e_schema", default=None)

_connect_args: dict = {}
if settings.env == "e2e":
    # Disable asyncpg prepared statement cache to prevent
    # InvalidCachedStatementError when E2E schemas are dropped/recreated
    _connect_args["statement_cache_size"] = 0
if settings.postgres_ssl:
    import ssl

    _ssl_context = ssl.create_default_context()
    _connect_args["ssl"] = _ssl_context

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=_utc_now,
    )

    @property
    def created_at(self) -> datetime:
        """Extract creation timestamp from UUID7."""
        u = UUID(self.id.hex)
        return datetime.fromtimestamp(u.time / 1000.0, tz=UTC)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            # Set search_path if E2E schema is specified in context
            schema = e2e_schema_context.get()
            if schema:
                await session.execute(text(f"SET search_path TO {schema}, public"))

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
