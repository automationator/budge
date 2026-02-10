from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EnvelopeGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    sort_order: int = 0


class EnvelopeGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    sort_order: int | None = None


class EnvelopeGroupResponse(BaseModel):
    id: UUID
    budget_id: UUID
    name: str
    icon: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
