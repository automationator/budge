"""Router for notification endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.notifications import service
from src.notifications.models import NotificationType
from src.notifications.schemas import (
    MarkNotificationsRequest,
    NotificationCountResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
)

router = APIRouter(prefix="/budgets/{budget_id}/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
)
async def list_notifications(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    include_dismissed: bool = False,
    limit: int = 50,
) -> list[NotificationResponse]:
    """Get notifications for the current user.

    Also generates any new notifications based on current data state.
    """
    # Generate any new notifications
    await service.generate_notifications(session, ctx.budget.id, ctx.user.id)
    await session.flush()

    # Fetch notifications
    notifications = await service.get_notifications(
        session, ctx.budget.id, ctx.user.id, include_dismissed, limit
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get(
    "/count",
    response_model=NotificationCountResponse,
)
async def get_notification_count(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> NotificationCountResponse:
    """Get count of unread notifications."""
    count = await service.get_unread_count(session, ctx.budget.id, ctx.user.id)
    return NotificationCountResponse(unread_count=count)


@router.post(
    "/mark-read",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_notifications_read(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_UPDATE]),
    ],
    request: MarkNotificationsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Mark notifications as read."""
    await service.mark_notifications_read(
        session, ctx.budget.id, ctx.user.id, request.notification_ids
    )


@router.post(
    "/mark-dismissed",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_notifications_dismissed(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_UPDATE]),
    ],
    request: MarkNotificationsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Mark notifications as dismissed."""
    await service.mark_notifications_dismissed(
        session, ctx.budget.id, ctx.user.id, request.notification_ids
    )


@router.get(
    "/preferences",
    response_model=list[NotificationPreferenceResponse],
)
async def list_preferences(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[NotificationPreferenceResponse]:
    """Get notification preferences for the current user.

    Returns preferences for all notification types, creating defaults if needed.
    """
    # Ensure all preferences exist
    for notification_type in NotificationType:
        await service.get_or_create_preference(
            session, ctx.budget.id, ctx.user.id, notification_type
        )

    prefs = await service.get_preferences(session, ctx.budget.id, ctx.user.id)
    return [NotificationPreferenceResponse.model_validate(p) for p in prefs]


@router.patch(
    "/preferences/{notification_type}",
    response_model=NotificationPreferenceResponse,
)
async def update_preference(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.NOTIFICATIONS_UPDATE]),
    ],
    notification_type: NotificationType,
    preference_in: NotificationPreferenceUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> NotificationPreferenceResponse:
    """Update a notification preference."""
    pref = await service.update_preference(
        session,
        ctx.budget.id,
        ctx.user.id,
        notification_type,
        preference_in.is_enabled,
        preference_in.low_balance_threshold,
        preference_in.upcoming_expense_days,
    )
    return NotificationPreferenceResponse.model_validate(pref)
