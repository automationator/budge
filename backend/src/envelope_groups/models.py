from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class EnvelopeGroup(Base):
    __tablename__ = "envelope_groups"
    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_budget_envelope_group_name"),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str | None] = mapped_column(String(10), default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
