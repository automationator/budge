from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Payee(Base):
    __tablename__ = "payees"
    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_budget_payee_name"),
    )

    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str | None] = mapped_column(String(10), default=None)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    default_envelope_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("envelopes.id", ondelete="SET NULL"),
        default=None,
    )
