from pydantic import BaseModel


class SystemSettingsResponse(BaseModel):
    """Response schema for system settings."""

    registration_enabled: bool

    model_config = {"from_attributes": True}


class SystemSettingsUpdate(BaseModel):
    """Request schema for updating system settings."""

    registration_enabled: bool | None = None


class RegistrationStatusResponse(BaseModel):
    """Public response for registration status check."""

    registration_enabled: bool


class VersionResponse(BaseModel):
    """Response schema for version check."""

    current_version: str
    latest_version: str | None = None
    update_available: bool = False
    release_url: str | None = None
    error: str | None = None
