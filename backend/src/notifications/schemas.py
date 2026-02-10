"""Schemas for notifications API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.notifications.models import NotificationType


class NotificationResponse(BaseModel):
    """Response schema for a notification."""

    id: UUID
    budget_id: UUID
    user_id: UUID | None
    notification_type: NotificationType
    title: str
    message: str
    related_entity_type: str | None
    related_entity_id: UUID | None
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationPreferenceResponse(BaseModel):
    """Response schema for notification preferences."""

    id: UUID
    budget_id: UUID
    user_id: UUID
    notification_type: NotificationType
    is_enabled: bool
    low_balance_threshold: int | None
    upcoming_expense_days: int | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    """Update schema for notification preferences."""

    is_enabled: bool | None = None
    low_balance_threshold: int | None = Field(default=None, ge=0)
    upcoming_expense_days: int | None = Field(default=None, ge=1, le=365)


class MarkNotificationsRequest(BaseModel):
    """Request to mark notifications as read/dismissed."""

    notification_ids: list[UUID] = Field(min_length=1)


class NotificationCountResponse(BaseModel):
    """Response with unread notification count."""

    unread_count: int
