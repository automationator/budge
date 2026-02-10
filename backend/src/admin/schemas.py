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
