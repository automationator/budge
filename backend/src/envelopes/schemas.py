from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EnvelopeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    envelope_group_id: UUID | None = None
    sort_order: int = 0
    is_active: bool = True
    target_balance: int | None = None


class EnvelopeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    envelope_group_id: UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_starred: bool | None = None
    target_balance: int | None = None


class EnvelopeResponse(BaseModel):
    id: UUID
    budget_id: UUID
    envelope_group_id: UUID | None
    linked_account_id: UUID | None
    name: str
    icon: str | None
    description: str | None
    sort_order: int
    is_active: bool
    is_starred: bool
    is_unallocated: bool
    current_balance: int
    target_balance: int | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class EnvelopeSummaryResponse(BaseModel):
    """Summary of envelope-related financial data for a budget."""

    ready_to_assign: int  # Unallocated balance (non-CC accounts - all envelopes)
    unfunded_cc_debt: int  # CC debt not covered by CC envelope balances


# Budget summary schemas (YNAB-style view)
class EnvelopeBudgetItem(BaseModel):
    """Budget item for a single envelope with date-filtered metrics."""

    envelope_id: UUID
    envelope_name: str
    envelope_group_id: UUID | None
    linked_account_id: UUID | None
    icon: str | None
    sort_order: int
    is_starred: bool
    activity: int  # Sum of all allocations (transactions + transfers) in date range
    balance: int  # current_balance (not date-filtered)
    target_balance: int | None


class EnvelopeGroupBudgetSummary(BaseModel):
    """Budget summary for an envelope group with aggregated metrics."""

    group_id: UUID | None
    group_name: str | None
    icon: str | None
    sort_order: int
    envelopes: list[EnvelopeBudgetItem]
    total_activity: int
    total_balance: int


class EnvelopeBudgetSummaryResponse(BaseModel):
    """Complete budget summary with all envelopes grouped."""

    start_date: date
    end_date: date
    ready_to_assign: int
    total_activity: int
    total_balance: int
    groups: list[EnvelopeGroupBudgetSummary]


# Activity detail schemas
class EnvelopeActivityItem(BaseModel):
    """Individual activity item (transaction or transfer) for an envelope."""

    allocation_id: UUID
    transaction_id: UUID | None  # None for transfers
    date: date
    activity_type: str  # "transaction" or "transfer"

    # Transaction fields (None for transfers)
    account_id: UUID | None
    account_name: str | None
    payee_id: UUID | None
    payee_name: str | None
    memo: str | None

    # Transfer fields (None for transactions)
    counterpart_envelope_name: str | None = None

    amount: int


class EnvelopeActivityResponse(BaseModel):
    """Activity details for an envelope in a date range."""

    envelope_id: UUID
    envelope_name: str
    start_date: date
    end_date: date
    items: list[EnvelopeActivityItem]
    total: int


class EnvelopeBalanceCorrectionResponse(BaseModel):
    """Result of an envelope balance correction."""

    envelope_id: UUID | None
    envelope_name: str
    old_balance: int
    new_balance: int
