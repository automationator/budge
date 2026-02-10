from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.budgets.models import BudgetMembership
from src.database import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

    budget_memberships: Mapped[list[BudgetMembership]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
