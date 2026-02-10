"""Schemas for data export/import functionality."""

from datetime import date as DateType
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.accounts.schemas import AccountResponse
from src.allocation_rules.schemas import AllocationRuleResponse
from src.allocations.schemas import AllocationResponse
from src.budgets.models import DefaultIncomeAllocation
from src.envelope_groups.schemas import EnvelopeGroupResponse
from src.envelopes.schemas import EnvelopeResponse
from src.locations.schemas import LocationResponse
from src.payees.schemas import PayeeResponse
from src.recurring_transactions.schemas import RecurringTransactionResponse
from src.transactions.models import TransactionStatus, TransactionType


class TransactionExport(BaseModel):
    """Transaction for export - excludes embedded allocations.

    This is a standalone schema (not inheriting from TransactionResponse) because:
    - Allocations are exported as a separate top-level array
    - Standalone allocations exist (transaction_id = None)
    - Import logic needs group_id mapping across all allocations
    - The allocations relationship is lazy='raise' on the ORM model
    """

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
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class BudgetExport(BaseModel):
    """Budget metadata for export."""

    name: str
    default_income_allocation: DefaultIncomeAllocation = DefaultIncomeAllocation.RULES


class ExportData(BaseModel):
    """Complete export data structure."""

    version: str = Field(default="1.0", description="Export format version")
    exported_at: datetime
    budget: BudgetExport
    accounts: list[AccountResponse]
    envelope_groups: list[EnvelopeGroupResponse]
    envelopes: list[EnvelopeResponse]
    payees: list[PayeeResponse]
    locations: list[LocationResponse]
    allocation_rules: list[AllocationRuleResponse]
    recurring_transactions: list[RecurringTransactionResponse]
    transactions: list[TransactionExport]
    allocations: list[AllocationResponse]


class ExportResponse(BaseModel):
    """API response for export endpoint."""

    data: ExportData


# Import schemas - for validation


class ImportData(BaseModel):
    """Import data structure - same as export but validated on input."""

    version: str = Field(description="Export format version")
    exported_at: datetime
    budget: BudgetExport
    accounts: list[AccountResponse]
    envelope_groups: list[EnvelopeGroupResponse]
    envelopes: list[EnvelopeResponse]
    payees: list[PayeeResponse]
    locations: list[LocationResponse]
    allocation_rules: list[AllocationRuleResponse]
    recurring_transactions: list[RecurringTransactionResponse]
    transactions: list[TransactionExport]
    allocations: list[AllocationResponse]


class ImportRequest(BaseModel):
    """API request for import endpoint."""

    data: ImportData
    clear_existing: bool = Field(
        default=False,
        description="If true, delete all existing budget data before import",
    )
    password: str = Field(
        min_length=1,
        description="User's password for confirmation",
    )


class ImportResult(BaseModel):
    """Result of an import operation."""

    success: bool
    accounts_imported: int
    envelope_groups_imported: int
    envelopes_imported: int
    payees_imported: int
    locations_imported: int
    allocation_rules_imported: int
    recurring_transactions_imported: int
    transactions_imported: int
    allocations_imported: int
    errors: list[str] = Field(default_factory=list)
