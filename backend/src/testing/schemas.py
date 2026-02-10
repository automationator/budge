from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ResetRequest(BaseModel):
    worker_id: str  # e.g., "w0", "w1", "w2"


class ResetResponse(BaseModel):
    schema_name: str
    status: str


class UserFactoryRequest(BaseModel):
    worker_id: str
    username: str
    password: str = "TestPassword123!"
    is_admin: bool | None = None


class UserFactoryResponse(BaseModel):
    user_id: UUID
    budget_id: UUID
    access_token: str
    refresh_token: str


class AccountFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    name: str
    account_type: str = "checking"
    include_in_budget: bool = True
    starting_balance: int = 0  # in cents


class AccountFactoryResponse(BaseModel):
    id: UUID
    name: str
    account_type: str
    include_in_budget: bool
    cleared_balance: int
    uncleared_balance: int


class EnvelopeFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    name: str
    group_name: str | None = None
    target_balance: int | None = None
    is_starred: bool = False


class EnvelopeFactoryResponse(BaseModel):
    id: UUID
    name: str
    envelope_group_id: UUID | None
    current_balance: int
    target_balance: int | None
    is_starred: bool


class TransactionFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    account_id: UUID
    amount: int  # in cents
    payee_name: str | None = None
    envelope_id: UUID | None = None
    transaction_date: date | None = None
    memo: str | None = None
    is_cleared: bool = False


class TransactionFactoryResponse(BaseModel):
    id: UUID
    account_id: UUID
    amount: int
    payee_id: UUID | None
    date: date
    is_cleared: bool
    is_reconciled: bool


class ReconcileFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    account_id: UUID
    actual_balance: int  # in cents


class ReconcileFactoryResponse(BaseModel):
    transactions_reconciled: int
    adjustment_transaction_id: UUID | None


class PayeeFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    name: str


class PayeeFactoryResponse(BaseModel):
    id: UUID
    name: str


class EnvelopeGroupFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    name: str


class EnvelopeGroupFactoryResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int


class BudgetFactoryRequest(BaseModel):
    worker_id: str
    user_id: UUID
    name: str


class BudgetFactoryResponse(BaseModel):
    id: UUID
    name: str


class LocationFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    name: str


class LocationFactoryResponse(BaseModel):
    id: UUID
    name: str


class AllocationRuleFactoryRequest(BaseModel):
    worker_id: str
    budget_id: UUID
    envelope_id: UUID
    rule_type: str = "fixed"  # fixed, percentage, fill_to_target, remainder, period_cap
    amount: int = 0  # in cents or basis points (for percentage)
    priority: int = 1
    is_active: bool = True
    name: str | None = None
    cap_period_value: int = 1
    cap_period_unit: str | None = None  # "week", "month", "year"


class AllocationRuleFactoryResponse(BaseModel):
    id: UUID
    envelope_id: UUID
    rule_type: str
    amount: int
    priority: int
    is_active: bool
    cap_period_value: int
    cap_period_unit: str | None


class SetRegistrationRequest(BaseModel):
    worker_id: str
    enabled: bool


class SetRegistrationResponse(BaseModel):
    registration_enabled: bool
