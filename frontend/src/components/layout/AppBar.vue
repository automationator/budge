<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useDisplay, useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useNavDrawer } from '@/composables/useNavDrawer'

const { mobile } = useDisplay()
const theme = useTheme()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const { toggleDrawer } = useNavDrawer()

const isDark = computed(() => theme.global.current.value.dark)

function toggleTheme() {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
  localStorage.setItem('theme', theme.global.name.value)
}

const showNotifications = ref(false)

// Fetch notification count on mount and when budget changes
onMounted(() => {
  if (authStore.currentBudgetId) {
    notificationsStore.fetchUnreadCount()
  }
})

watch(() => authStore.currentBudgetId, (budgetId) => {
  if (budgetId) {
    notificationsStore.fetchUnreadCount()
  }
})

async function openNotifications() {
  showNotifications.value = true
  await notificationsStore.fetchNotifications()
}

async function markAllRead() {
  const unreadIds = notificationsStore.notifications
    .filter((n) => !n.is_read)
    .map((n) => n.id)
  if (unreadIds.length > 0) {
    await notificationsStore.markAsRead(unreadIds)
  }
}

async function dismissNotification(id: string) {
  await notificationsStore.markAsDismissed([id])
}

function handleLogout() {
  authStore.logout()
}
</script>

<template>
  <v-app-bar
    color="primary"
    density="comfortable"
  >
    <!-- Menu button (mobile) -->
    <v-app-bar-nav-icon
      v-if="!mobile"
      @click="toggleDrawer"
    />

    <v-app-bar-title class="d-none d-sm-block">
      Budge
    </v-app-bar-title>

    <v-spacer />

    <!-- Theme toggle -->
    <v-btn
      icon
      @click="toggleTheme"
    >
      <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
    </v-btn>

    <!-- Notifications -->
    <v-btn
      icon
      @click="openNotifications"
    >
      <v-badge
        v-if="notificationsStore.hasUnread"
        :content="notificationsStore.unreadCount"
        color="error"
      >
        <v-icon>mdi-bell</v-icon>
      </v-badge>
      <v-icon v-else>
        mdi-bell-outline
      </v-icon>
    </v-btn>

    <!-- User menu -->
    <v-menu>
      <template #activator="{ props }">
        <v-btn
          icon
          v-bind="props"
        >
          <v-icon>mdi-account-circle</v-icon>
        </v-btn>
      </template>
      <v-list>
        <v-list-item>
          <v-list-item-title>@{{ authStore.user?.username }}</v-list-item-title>
        </v-list-item>
        <v-divider />
        <v-list-item to="/settings">
          <template #prepend>
            <v-icon>mdi-cog</v-icon>
          </template>
          <v-list-item-title>Settings</v-list-item-title>
        </v-list-item>
        <v-list-item @click="handleLogout">
          <template #prepend>
            <v-icon>mdi-logout</v-icon>
          </template>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-app-bar>

  <!-- Notifications drawer -->
  <v-navigation-drawer
    v-model="showNotifications"
    location="right"
    temporary
    width="350"
  >
    <v-toolbar
      color="primary"
      density="compact"
    >
      <v-toolbar-title>Notifications</v-toolbar-title>
      <v-spacer />
      <v-btn
        v-if="notificationsStore.hasUnread"
        variant="text"
        size="small"
        @click="markAllRead"
      >
        Mark all read
      </v-btn>
    </v-toolbar>

    <v-list v-if="notificationsStore.notifications.length > 0">
      <v-list-item
        v-for="notification in notificationsStore.notifications"
        :key="notification.id"
        :class="{ 'bg-blue-lighten-5': !notification.is_read }"
      >
        <template #prepend>
          <v-icon
            :color="notification.is_read ? 'grey' : 'primary'"
          >
            {{
              notification.notification_type === 'low_balance' ? 'mdi-alert' :
              notification.notification_type === 'goal_reached' ? 'mdi-check-circle' :
              notification.notification_type === 'upcoming_expense' ? 'mdi-calendar-alert' :
              'mdi-bell'
            }}
          </v-icon>
        </template>

        <v-list-item-title>{{ notification.title }}</v-list-item-title>
        <v-list-item-subtitle class="text-wrap">
          {{ notification.message }}
        </v-list-item-subtitle>

        <template #append>
          <v-btn
            icon
            size="small"
            variant="text"
            @click.stop="dismissNotification(notification.id)"
          >
            <v-icon size="small">
              mdi-close
            </v-icon>
          </v-btn>
        </template>
      </v-list-item>
    </v-list>

    <v-card-text
      v-else
      class="text-center text-grey"
    >
      No notifications
    </v-card-text>
  </v-navigation-drawer>
</template>
