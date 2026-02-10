from datetime import date as DateType
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AllocationInput(BaseModel):
    """Input for creating an allocation as part of a transaction."""

    envelope_id: UUID
    amount: int  # Cents, can be negative (expense) or positive (income)
    memo: str | None = Field(default=None, max_length=500)
    allocation_rule_id: UUID | None = None  # Set when created by a rule


class EnvelopeTransferCreate(BaseModel):
    """Input for creating an envelope-to-envelope transfer."""

    source_envelope_id: UUID
    destination_envelope_id: UUID
    amount: int = Field(gt=0)  # Must be positive, always moves from source to dest
    memo: str | None = Field(default=None, max_length=500)
    date: DateType | None = None  # Optional date, defaults to today


class AllocationUpdate(BaseModel):
    """Input for updating an allocation."""

    envelope_id: UUID | None = None
    amount: int | None = None
    memo: str | None = Field(default=None, max_length=500)


class AllocationResponse(BaseModel):
    id: UUID
    budget_id: UUID
    envelope_id: UUID
    transaction_id: UUID | None
    allocation_rule_id: UUID | None
    group_id: UUID
    amount: int
    execution_order: int
    memo: str | None
    date: DateType  # Date of allocation (transaction date or transfer date)
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class EnvelopeTransferResponse(BaseModel):
    """Response for an envelope transfer.

    For transfers involving the unallocated envelope, one allocation may be
    None since the unallocated balance is calculated dynamically.
    """

    source_allocation: AllocationResponse | None
    destination_allocation: AllocationResponse | None
