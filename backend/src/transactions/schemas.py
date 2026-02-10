from datetime import date as DateType
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.allocations.schemas import AllocationInput, AllocationResponse
from src.transactions.models import TransactionStatus, TransactionType


class TransactionCreate(BaseModel):
    account_id: UUID
    payee_id: UUID | None = None
    location_id: UUID | None = None
    user_id: UUID | None = None
    date: DateType
    amount: int
    is_cleared: bool = False
    memo: str | None = Field(default=None, max_length=500)
    transaction_type: TransactionType = TransactionType.STANDARD
    allocations: list[AllocationInput] | None = None
    apply_allocation_rules: bool = (
        False  # When true, auto-distribute income via allocation rules
    )

    @model_validator(mode="after")
    def validate_payee_for_transaction_type(self) -> TransactionCreate:
        if self.transaction_type == TransactionType.STANDARD and self.payee_id is None:
            raise ValueError("payee_id is required for standard transactions")
        if (
            self.transaction_type == TransactionType.ADJUSTMENT
            and self.payee_id is not None
        ):
            raise ValueError("payee_id must be null for adjustment transactions")
        if self.transaction_type == TransactionType.TRANSFER:
            raise ValueError("Use the /transfers endpoint to create transfers")
        return self


class TransactionUpdate(BaseModel):
    account_id: UUID | None = None
    payee_id: UUID | None = None
    location_id: UUID | None = None
    user_id: UUID | None = None
    date: DateType | None = None
    amount: int | None = None
    is_cleared: bool | None = None
    memo: str | None = Field(default=None, max_length=500)
    allocations: list[AllocationInput] | None = None  # Replace all allocations


class TransactionResponse(BaseModel):
    id: UUID
    budget_id: UUID
    account_id: UUID
    payee_id: UUID | None
    location_id: UUID | None
    user_id: UUID | None
    date: DateType
    amount: int
    is_cleared: bool
    is_reconciled: bool
    memo: str | None
    transaction_type: TransactionType
    status: TransactionStatus
    recurring_transaction_id: UUID | None
    occurrence_index: int | None
    is_modified: bool
    linked_transaction_id: UUID | None
    linked_account_id: UUID | None = None
    allocations: list[AllocationResponse]
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ReconcileRequest(BaseModel):
    """Request to reconcile an account balance."""

    actual_balance: int = Field(description="The actual balance in cents")


class ReconcileResponse(BaseModel):
    """Response from reconciling an account."""

    transactions_reconciled: int
    adjustment_transaction: TransactionResponse | None = None


class TransferCreate(BaseModel):
    """Create a transfer between two accounts."""

    source_account_id: UUID
    destination_account_id: UUID
    amount: int = Field(gt=0, description="Positive amount to transfer in cents")
    date: DateType
    memo: str | None = Field(default=None, max_length=500)
    is_cleared: bool = False
    user_id: UUID | None = None
    envelope_id: UUID | None = None  # Required for budget -> tracking transfers

    @model_validator(mode="after")
    def validate_different_accounts(self) -> TransferCreate:
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination accounts must be different")
        return self


class TransferUpdate(BaseModel):
    """Update a transfer (updates both linked transactions)."""

    source_account_id: UUID | None = None
    destination_account_id: UUID | None = None
    amount: int | None = Field(default=None, gt=0)
    date: DateType | None = None
    memo: str | None = Field(default=None, max_length=500)
    source_is_cleared: bool | None = None
    destination_is_cleared: bool | None = None
    user_id: UUID | None = None
    envelope_id: UUID | None = None  # For budget -> tracking transfers

    @model_validator(mode="after")
    def validate_different_accounts(self) -> TransferUpdate:
        if (
            self.source_account_id is not None
            and self.destination_account_id is not None
            and self.source_account_id == self.destination_account_id
        ):
            raise ValueError("Source and destination accounts must be different")
        return self


class TransferResponse(BaseModel):
    """Response containing both sides of a transfer."""

    source_transaction: TransactionResponse
    destination_transaction: TransactionResponse
