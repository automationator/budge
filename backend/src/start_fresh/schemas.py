"""Schemas for Start Fresh endpoints."""

from enum import StrEnum

from pydantic import BaseModel, Field


class DataCategory(StrEnum):
    """Categories of data that can be deleted."""

    TRANSACTIONS = "transactions"  # Includes allocations
    RECURRING = "recurring"  # Recurring transactions
    ENVELOPES = "envelopes"  # Includes groups and allocation rules
    ACCOUNTS = "accounts"  # Cascade deletes transactions
    PAYEES = "payees"  # Only unlinked payees when selective
    LOCATIONS = "locations"
    ALLOCATIONS = "allocations"  # Clear allocations and reset envelope balances
    ALL = "all"  # Everything


class StartFreshRequest(BaseModel):
    """Request to delete budget data."""

    password: str = Field(min_length=1, description="User's password for confirmation")
    categories: list[DataCategory] = Field(
        min_length=1, description="Categories of data to delete"
    )


class StartFreshPreview(BaseModel):
    """Preview of what will be deleted."""

    transactions_count: int = 0
    allocations_count: int = 0
    recurring_transactions_count: int = 0
    envelopes_count: int = 0
    envelope_groups_count: int = 0
    allocation_rules_count: int = 0
    accounts_count: int = 0
    payees_count: int = 0
    locations_count: int = 0
    envelopes_cleared_count: int = 0  # Envelopes that will have balances reset


class StartFreshResponse(BaseModel):
    """Response after deletion."""

    success: bool
    deleted: StartFreshPreview
    message: str
