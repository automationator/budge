from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.accounts.models import AccountType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_type: AccountType
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    include_in_budget: bool = True
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    account_type: AccountType | None = None
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    include_in_budget: bool | None = None
    is_active: bool | None = None


class AccountResponse(BaseModel):
    id: UUID
    budget_id: UUID
    name: str
    account_type: AccountType
    icon: str | None
    description: str | None
    sort_order: int
    include_in_budget: bool
    is_active: bool
    cleared_balance: int
    uncleared_balance: int
    last_reconciled_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class BalanceCorrectionResponse(BaseModel):
    account_id: UUID
    account_name: str
    old_cleared: int
    old_uncleared: int
    new_cleared: int
    new_uncleared: int
