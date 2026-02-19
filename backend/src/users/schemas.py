import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _validate_password_complexity(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[^A-Za-z0-9]", v):
        raise ValueError("Password must contain at least one special character")
    return v


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=8)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password_complexity(v)


class UserResponse(BaseModel):
    id: UUID
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
