from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PayeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)


class PayeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    default_envelope_id: UUID | None = Field(default=None)


class PayeeResponse(BaseModel):
    id: UUID
    budget_id: UUID
    name: str
    icon: str | None
    description: str | None
    default_envelope_id: UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class DefaultEnvelopeResponse(BaseModel):
    """Response schema for default envelope lookup."""

    envelope_id: UUID | None
