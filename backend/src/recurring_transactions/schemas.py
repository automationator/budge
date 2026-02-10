from datetime import date as DateType
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.recurring_transactions.models import FrequencyUnit


class RecurringTransactionCreate(BaseModel):
    account_id: UUID
    destination_account_id: UUID | None = None  # Set for transfers only
    payee_id: UUID | None = None  # Required for regular, null for transfers
    location_id: UUID | None = None
    user_id: UUID | None = None
    envelope_id: UUID | None = None
    frequency_value: int = Field(ge=1, le=365)
    frequency_unit: FrequencyUnit
    start_date: DateType
    end_date: DateType | None = None
    amount: int
    memo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_transaction_type(self) -> RecurringTransactionCreate:
        if self.destination_account_id:
            # It's a transfer
            if self.payee_id:
                raise ValueError("payee_id must be null for transfers")
            if self.account_id == self.destination_account_id:
                raise ValueError("Source and destination accounts must be different")
        else:
            # Regular transaction
            if not self.payee_id:
                raise ValueError("payee_id is required for non-transfer transactions")
        return self


class RecurringTransactionUpdate(BaseModel):
    account_id: UUID | None = None
    destination_account_id: UUID | None = None
    payee_id: UUID | None = None
    location_id: UUID | None = None
    user_id: UUID | None = None
    envelope_id: UUID | None = None
    frequency_value: int | None = Field(default=None, ge=1, le=365)
    frequency_unit: FrequencyUnit | None = None
    start_date: DateType | None = None
    end_date: DateType | None = None
    amount: int | None = None
    memo: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_different_accounts(self) -> RecurringTransactionUpdate:
        if (
            self.account_id is not None
            and self.destination_account_id is not None
            and self.account_id == self.destination_account_id
        ):
            raise ValueError("Source and destination accounts must be different")
        return self


class RecurringTransactionResponse(BaseModel):
    id: UUID
    budget_id: UUID
    account_id: UUID
    destination_account_id: UUID | None
    payee_id: UUID | None
    location_id: UUID | None
    user_id: UUID | None
    envelope_id: UUID | None
    frequency_value: int
    frequency_unit: FrequencyUnit
    start_date: DateType
    end_date: DateType | None
    amount: int
    memo: str | None
    next_occurrence_date: DateType
    next_scheduled_date: DateType | None = None  # Earliest scheduled transaction date
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
