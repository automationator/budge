from uuid import UUID

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: UUID | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
