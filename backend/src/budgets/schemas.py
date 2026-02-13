from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.budgets.models import BudgetRole, DefaultIncomeAllocation


class CreateBudgetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateBudgetRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    default_income_allocation: DefaultIncomeAllocation | None = None


class DeleteBudgetRequest(BaseModel):
    password: str = Field(min_length=1, description="User's password for confirmation")


class MemberRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class AddMemberRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    role: BudgetRole = BudgetRole.MEMBER


class MemberRoleUpdate(BaseModel):
    role: BudgetRole


class ScopeModification(BaseModel):
    scope: str = Field(min_length=1, max_length=100)


class BudgetMemberResponse(BaseModel):
    id: UUID
    username: str

    model_config = {"from_attributes": True}


class BudgetMemberWithRoleResponse(BaseModel):
    id: UUID
    username: str
    role: BudgetRole
    effective_scopes: list[str]

    model_config = {"from_attributes": True}


class MemberScopesResponse(BaseModel):
    user_id: UUID
    role: BudgetRole
    role_scopes: list[str]
    scope_additions: list[str]
    scope_removals: list[str]
    effective_scopes: list[str]


class BalanceCheckResponse(BaseModel):
    needs_repair: bool


class BudgetResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    default_income_allocation: DefaultIncomeAllocation
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
