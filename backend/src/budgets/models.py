from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ARRAY, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User


class BudgetRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class DefaultIncomeAllocation(StrEnum):
    RULES = "rules"
    ENVELOPE = "envelope"
    UNALLOCATED = "unallocated"


class Budget(Base):
    __tablename__ = "budgets"

    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    default_income_allocation: Mapped[str] = mapped_column(
        String(20), default=DefaultIncomeAllocation.RULES
    )

    members: Mapped[list[BudgetMembership]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
    )


class BudgetMembership(Base):
    __tablename__ = "user_budgets"
    __table_args__ = (UniqueConstraint("user_id", "budget_id", name="uq_user_budget"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE")
    )
    role: Mapped[BudgetRole] = mapped_column(
        PgEnum(
            BudgetRole,
            name="budget_role",
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=BudgetRole.MEMBER,
    )
    scope_additions: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        server_default="{}",
    )
    scope_removals: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        server_default="{}",
    )

    user: Mapped[User] = relationship(back_populates="budget_memberships")
    budget: Mapped[Budget] = relationship(back_populates="members")
