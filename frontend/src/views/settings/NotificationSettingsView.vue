<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import {
  getNotificationPreferences,
  updateNotificationPreference,
} from '@/api/notifications'
import type { NotificationPreference, NotificationType } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const preferences = ref<NotificationPreference[]>([])
const saving = ref<Record<string, boolean>>({})

interface NotificationConfig {
  type: NotificationType
  title: string
  description: string
  icon: string
  hasThreshold?: boolean
  hasDays?: boolean
}

const notificationConfigs: NotificationConfig[] = [
  {
    type: 'low_balance',
    title: 'Low Balance Alerts',
    description: 'Get notified when an envelope balance falls below your threshold',
    icon: 'mdi-alert-circle',
    hasThreshold: true,
  },
  {
    type: 'upcoming_expense',
    title: 'Upcoming Expenses',
    description: 'Reminders for scheduled recurring transactions',
    icon: 'mdi-calendar-alert',
    hasDays: true,
  },
  {
    type: 'recurring_not_funded',
    title: 'Recurring Not Funded',
    description: 'Alert when a recurring expense envelope cannot cover the transaction',
    icon: 'mdi-cash-remove',
  },
  {
    type: 'goal_reached',
    title: 'Goal Reached',
    description: 'Celebrate when savings goals are met',
    icon: 'mdi-party-popper',
  },
]

const preferenceMap = computed(() => {
  const map: Record<string, NotificationPreference> = {}
  for (const pref of preferences.value) {
    map[pref.notification_type] = pref
  }
  return map
})

onMounted(async () => {
  await loadPreferences()
})

async function loadPreferences() {
  if (!authStore.currentBudgetId) return

  try {
    loading.value = true
    preferences.value = await getNotificationPreferences(authStore.currentBudgetId)
  } catch {
    showSnackbar('Failed to load notification preferences', 'error')
  } finally {
    loading.value = false
  }
}

async function toggleEnabled(type: NotificationType, enabled: boolean) {
  if (!authStore.currentBudgetId) return

  saving.value[type] = true
  try {
    const updated = await updateNotificationPreference(authStore.currentBudgetId, type, {
      is_enabled: enabled,
    })
    const index = preferences.value.findIndex((p) => p.notification_type === type)
    if (index >= 0) {
      preferences.value[index] = updated
    }
  } catch {
    showSnackbar('Failed to update preference', 'error')
  } finally {
    saving.value[type] = false
  }
}

async function updateThreshold(type: NotificationType, threshold: number | null) {
  if (!authStore.currentBudgetId) return

  saving.value[type] = true
  try {
    const updated = await updateNotificationPreference(authStore.currentBudgetId, type, {
      low_balance_threshold: threshold,
    })
    const index = preferences.value.findIndex((p) => p.notification_type === type)
    if (index >= 0) {
      preferences.value[index] = updated
    }
  } catch {
    showSnackbar('Failed to update threshold', 'error')
  } finally {
    saving.value[type] = false
  }
}

async function updateDays(type: NotificationType, days: number | null) {
  if (!authStore.currentBudgetId) return

  saving.value[type] = true
  try {
    const updated = await updateNotificationPreference(authStore.currentBudgetId, type, {
      upcoming_expense_days: days,
    })
    const index = preferences.value.findIndex((p) => p.notification_type === type)
    if (index >= 0) {
      preferences.value[index] = updated
    }
  } catch {
    showSnackbar('Failed to update days', 'error')
  } finally {
    saving.value[type] = false
  }
}

</script>

<template>
  <div>
    <v-btn
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
      @click="router.back()"
    >
      Back to Settings
    </v-btn>

    <h1 class="text-h4 mb-4">
      Notification Preferences
    </h1>

    <!-- Loading -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <v-card v-else>
      <v-list>
        <template
          v-for="config in notificationConfigs"
          :key="config.type"
        >
          <v-list-item>
            <template #prepend>
              <v-icon
                :icon="config.icon"
                class="mr-2"
              />
            </template>

            <v-list-item-title>{{ config.title }}</v-list-item-title>
            <v-list-item-subtitle>{{ config.description }}</v-list-item-subtitle>

            <template #append>
              <v-switch
                :model-value="preferenceMap[config.type]?.is_enabled ?? true"
                color="primary"
                hide-details
                :loading="saving[config.type]"
                @update:model-value="(val: boolean | null) => toggleEnabled(config.type, val ?? false)"
              />
            </template>
          </v-list-item>

          <!-- Threshold setting for low balance -->
          <v-expand-transition>
            <div
              v-if="config.hasThreshold && preferenceMap[config.type]?.is_enabled"
              class="px-4 pb-4"
            >
              <v-row
                align="center"
                class="ml-8"
              >
                <v-col cols="auto">
                  <span class="text-body-2 text-medium-emphasis">Alert when balance below:</span>
                </v-col>
                <v-col
                  cols="12"
                  sm="4"
                >
                  <v-text-field
                    :model-value="(preferenceMap[config.type]?.low_balance_threshold ?? 0) / 100"
                    type="number"
                    prefix="$"
                    density="compact"
                    hide-details
                    :loading="saving[config.type]"
                    @blur="(e: FocusEvent) => {
                      const val = parseFloat((e.target as HTMLInputElement).value)
                      if (!isNaN(val)) {
                        updateThreshold(config.type, Math.round(val * 100))
                      }
                    }"
                  />
                </v-col>
              </v-row>
            </div>
          </v-expand-transition>

          <!-- Days setting for upcoming expense -->
          <v-expand-transition>
            <div
              v-if="config.hasDays && preferenceMap[config.type]?.is_enabled"
              class="px-4 pb-4"
            >
              <v-row
                align="center"
                class="ml-8"
              >
                <v-col cols="auto">
                  <span class="text-body-2 text-medium-emphasis">Notify me:</span>
                </v-col>
                <v-col
                  cols="12"
                  sm="3"
                >
                  <v-text-field
                    :model-value="preferenceMap[config.type]?.upcoming_expense_days ?? 3"
                    type="number"
                    suffix="days before"
                    density="compact"
                    hide-details
                    min="1"
                    max="365"
                    :loading="saving[config.type]"
                    @blur="(e: FocusEvent) => {
                      const val = parseInt((e.target as HTMLInputElement).value, 10)
                      if (!isNaN(val) && val >= 1 && val <= 365) {
                        updateDays(config.type, val)
                      }
                    }"
                  />
                </v-col>
              </v-row>
            </div>
          </v-expand-transition>

          <v-divider v-if="config !== notificationConfigs[notificationConfigs.length - 1]" />
        </template>
      </v-list>
    </v-card>

    <v-card class="mt-4">
      <v-card-title class="text-subtitle-1">
        About Notifications
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis">
          Notifications appear in the app when you log in or navigate between pages.
          They help you stay on top of your budget and avoid surprises.
        </p>
      </v-card-text>
    </v-card>
  </div>
</template>
