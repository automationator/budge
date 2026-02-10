import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Notification } from '@/types'
import { useAuthStore } from './auth'
import apiClient from '@/api/client'

export const useNotificationsStore = defineStore('notifications', () => {
  // State
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)

  // Getters
  const hasUnread = computed(() => unreadCount.value > 0)

  // Actions
  async function fetchUnreadCount() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      const response = await apiClient.get<{ count: number }>(
        `/budgets/${authStore.currentBudgetId}/notifications/count`
      )
      unreadCount.value = response.data.count
    } catch (e) {
      console.error('Failed to fetch notification count:', e)
    }
  }

  async function fetchNotifications(includeDismissed = false) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      const response = await apiClient.get<Notification[]>(
        `/budgets/${authStore.currentBudgetId}/notifications`,
        { params: { include_dismissed: includeDismissed } }
      )
      notifications.value = response.data
    } catch (e) {
      console.error('Failed to fetch notifications:', e)
    } finally {
      loading.value = false
    }
  }

  async function markAsRead(notificationIds: string[]) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      await apiClient.post(`/budgets/${authStore.currentBudgetId}/notifications/mark-read`, {
        notification_ids: notificationIds,
      })

      // Update local state
      notifications.value = notifications.value.map((n) =>
        notificationIds.includes(n.id) ? { ...n, is_read: true } : n
      )

      // Refresh count
      await fetchUnreadCount()
    } catch (e) {
      console.error('Failed to mark notifications as read:', e)
    }
  }

  async function markAsDismissed(notificationIds: string[]) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      await apiClient.post(`/budgets/${authStore.currentBudgetId}/notifications/mark-dismissed`, {
        notification_ids: notificationIds,
      })

      // Remove from local state (unless showing dismissed)
      notifications.value = notifications.value.filter((n) => !notificationIds.includes(n.id))

      // Refresh count
      await fetchUnreadCount()
    } catch (e) {
      console.error('Failed to dismiss notifications:', e)
    }
  }

  async function generateNotifications() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      await apiClient.post(`/budgets/${authStore.currentBudgetId}/notifications/generate`)
      // Refresh after generating
      await fetchUnreadCount()
    } catch (e) {
      console.error('Failed to generate notifications:', e)
    }
  }

  function reset() {
    notifications.value = []
    unreadCount.value = 0
  }

  return {
    // State
    notifications,
    unreadCount,
    loading,
    // Getters
    hasUnread,
    // Actions
    fetchUnreadCount,
    fetchNotifications,
    markAsRead,
    markAsDismissed,
    generateNotifications,
    reset,
  }
})
