from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)


class LocationResponse(BaseModel):
    id: UUID
    budget_id: UUID
    name: str
    icon: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
