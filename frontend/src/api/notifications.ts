import apiClient from './client'
import type { Notification, NotificationPreference, NotificationType } from '@/types'

export interface NotificationPreferenceUpdate {
  is_enabled?: boolean
  low_balance_threshold?: number | null
  upcoming_expense_days?: number | null
}

export interface NotificationCountResponse {
  unread_count: number
}

export async function getNotifications(
  budgetId: string,
  includeDismissed = false,
  limit = 50
): Promise<Notification[]> {
  const response = await apiClient.get<Notification[]>(`/budgets/${budgetId}/notifications`, {
    params: { include_dismissed: includeDismissed, limit },
  })
  return response.data
}

export async function getNotificationCount(budgetId: string): Promise<NotificationCountResponse> {
  const response = await apiClient.get<NotificationCountResponse>(
    `/budgets/${budgetId}/notifications/count`
  )
  return response.data
}

export async function markNotificationsRead(
  budgetId: string,
  notificationIds: string[]
): Promise<void> {
  await apiClient.post(`/budgets/${budgetId}/notifications/mark-read`, {
    notification_ids: notificationIds,
  })
}

export async function markNotificationsDismissed(
  budgetId: string,
  notificationIds: string[]
): Promise<void> {
  await apiClient.post(`/budgets/${budgetId}/notifications/mark-dismissed`, {
    notification_ids: notificationIds,
  })
}

export async function getNotificationPreferences(
  budgetId: string
): Promise<NotificationPreference[]> {
  const response = await apiClient.get<NotificationPreference[]>(
    `/budgets/${budgetId}/notifications/preferences`
  )
  return response.data
}

export async function updateNotificationPreference(
  budgetId: string,
  notificationType: NotificationType,
  data: NotificationPreferenceUpdate
): Promise<NotificationPreference> {
  const response = await apiClient.patch<NotificationPreference>(
    `/budgets/${budgetId}/notifications/preferences/${notificationType}`,
    data
  )
  return response.data
}
