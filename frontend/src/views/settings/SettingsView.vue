<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getSystemSettings, updateSystemSettings, getVersionInfo } from '@/api/admin'
import { showSnackbar } from '@/App.vue'
import type { VersionInfo } from '@/types'

const theme = useTheme()
const authStore = useAuthStore()
const appStore = useAppStore()

// Admin state
const isAdmin = computed(() => authStore.user?.is_admin ?? false)
const registrationEnabled = ref(true)
const loadingAdminSettings = ref(false)
const savingAdminSettings = ref(false)
const versionInfo = ref<VersionInfo | null>(null)

onMounted(async () => {
  if (isAdmin.value) {
    await Promise.all([loadAdminSettings(), checkForUpdates()])
  }
})

async function checkForUpdates() {
  try {
    versionInfo.value = await getVersionInfo()
  } catch {
    // Silently fail — version check is non-critical
  }
}

async function loadAdminSettings() {
  try {
    loadingAdminSettings.value = true
    const settings = await getSystemSettings()
    registrationEnabled.value = settings.registration_enabled
  } catch {
    showSnackbar('Failed to load admin settings', 'error')
  } finally {
    loadingAdminSettings.value = false
  }
}

async function onRegistrationToggle(newValue: boolean | null) {
  if (newValue === null) return
  try {
    savingAdminSettings.value = true
    await updateSystemSettings({ registration_enabled: newValue })
    // Refresh app store so login page reflects the change
    await appStore.refreshRegistrationStatus()
    showSnackbar(newValue ? 'Registration enabled' : 'Registration disabled', 'success')
  } catch {
    // Revert since the API call failed
    registrationEnabled.value = !newValue
    showSnackbar('Failed to update settings', 'error')
  } finally {
    savingAdminSettings.value = false
  }
}

const isDark = computed({
  get: () => theme.global.current.value.dark,
  set: (value: boolean) => {
    theme.global.name.value = value ? 'dark' : 'light'
    localStorage.setItem('theme', theme.global.name.value)
  },
})

const editing = ref(false)
const saving = ref(false)

// Form fields
const username = ref(authStore.user?.username || '')

// Password change
const showPasswordDialog = ref(false)
const newPassword = ref('')
const confirmPassword = ref('')
const savingPassword = ref(false)

const displayName = computed(() => {
  return authStore.user?.username || 'User'
})

const initials = computed(() => {
  return authStore.user?.username?.charAt(0).toUpperCase() || 'U'
})

function startEditing() {
  username.value = authStore.user?.username || ''
  editing.value = true
}

function cancelEditing() {
  editing.value = false
}

async function saveProfile() {
  try {
    saving.value = true
    await authStore.updateUser({
      username: username.value.trim(),
    })
    editing.value = false
  } catch {
    showSnackbar('Failed to update profile', 'error')
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  if (newPassword.value !== confirmPassword.value) {
    showSnackbar('Passwords do not match', 'error')
    return
  }
  if (newPassword.value.length < 8) {
    showSnackbar('Password must be at least 8 characters', 'error')
    return
  }

  try {
    savingPassword.value = true
    await authStore.updateUser({
      password: newPassword.value,
    })
    showPasswordDialog.value = false
    newPassword.value = ''
    confirmPassword.value = ''
  } catch {
    showSnackbar('Failed to update password', 'error')
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">
      Settings
    </h1>

    <!-- Profile Card -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        <v-avatar
          color="primary"
          size="56"
          class="mr-4"
        >
          <span class="text-h5">{{ initials }}</span>
        </v-avatar>
        <div>
          <div class="text-h6">
            {{ displayName }}
          </div>
          <div class="text-body-2 text-medium-emphasis">
            @{{ authStore.user?.username }}
          </div>
        </div>
        <v-spacer />
        <v-btn
          v-if="!editing"
          variant="outlined"
          @click="startEditing"
        >
          Edit Profile
        </v-btn>
      </v-card-title>

      <v-card-text v-if="!editing">
        <v-row>
          <v-col
            cols="12"
            sm="6"
          >
            <div class="text-caption text-medium-emphasis">
              Username
            </div>
            <div class="text-body-1">
              @{{ authStore.user?.username }}
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-text v-else>
        <v-form @submit.prevent="saveProfile">
          <v-row>
            <v-col
              cols="12"
              sm="6"
            >
              <v-text-field
                v-model="username"
                label="Username"
                required
                density="compact"
              />
            </v-col>
          </v-row>

          <div class="d-flex gap-2 mt-4">
            <v-btn
              color="primary"
              type="submit"
              :loading="saving"
            >
              Save Changes
            </v-btn>
            <v-btn
              variant="outlined"
              @click="cancelEditing"
            >
              Cancel
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Security Card -->
    <v-card class="mb-4">
      <v-card-title>Security</v-card-title>
      <v-card-text>
        <v-btn
          variant="outlined"
          prepend-icon="mdi-lock"
          @click="showPasswordDialog = true"
        >
          Change Password
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- Appearance Card -->
    <v-card class="mb-4">
      <v-card-title>Appearance</v-card-title>
      <v-card-text>
        <v-switch
          v-model="isDark"
          label="Dark Mode"
          color="primary"
          hide-details
        />
      </v-card-text>
    </v-card>

    <!-- Admin Settings Card (only visible to admins) -->
    <v-card
      v-if="isAdmin"
      class="mb-4"
    >
      <v-card-title>
        <v-icon class="mr-2">
          mdi-shield-crown
        </v-icon>
        Admin Settings
      </v-card-title>
      <v-card-text>
        <v-alert
          v-if="versionInfo?.update_available"
          type="info"
          variant="tonal"
          class="mb-4"
        >
          <div>
            A new version of Budge is available: <strong>{{ versionInfo.latest_version }}</strong>
            (current: {{ versionInfo.current_version }})
          </div>
          <div class="text-caption mt-1">
            <code>docker compose pull && docker compose up -d</code>
          </div>
          <v-btn
            v-if="versionInfo.release_url"
            size="small"
            variant="text"
            :href="versionInfo.release_url"
            target="_blank"
            class="mt-2 px-0"
          >
            View Release Notes
          </v-btn>
        </v-alert>

        <v-switch
          v-model="registrationEnabled"
          label="Allow new user registration"
          color="primary"
          :loading="loadingAdminSettings || savingAdminSettings"
          :disabled="loadingAdminSettings || savingAdminSettings"
          hide-details
          @update:model-value="onRegistrationToggle"
        />
        <div class="text-caption text-medium-emphasis mt-2">
          When disabled, only existing users can log in. New users cannot create accounts.
        </div>

        <div
          v-if="versionInfo"
          class="text-caption text-medium-emphasis mt-4"
        >
          <template v-if="versionInfo.error">
            Version: {{ versionInfo.current_version }} ({{ versionInfo.error }})
          </template>
          <template v-else>
            Version: {{ versionInfo.current_version }}
          </template>
        </div>
      </v-card-text>
    </v-card>

    <!-- Navigation Links -->
    <v-list>
      <v-list-item
        to="/settings/budget-settings"
        prepend-icon="mdi-account-group"
      >
        <v-list-item-title>Budget Settings</v-list-item-title>
        <v-list-item-subtitle>Manage budget members, rename, or delete budget</v-list-item-subtitle>
        <template #append>
          <v-icon>mdi-chevron-right</v-icon>
        </template>
      </v-list-item>

      <v-list-item
        to="/settings/notifications"
        prepend-icon="mdi-bell-cog"
      >
        <v-list-item-title>Notification Preferences</v-list-item-title>
        <v-list-item-subtitle>Configure alerts</v-list-item-subtitle>
        <template #append>
          <v-icon>mdi-chevron-right</v-icon>
        </template>
      </v-list-item>

      <v-list-item
        to="/settings/locations"
        prepend-icon="mdi-map-marker"
      >
        <v-list-item-title>Manage Locations</v-list-item-title>
        <v-list-item-subtitle>Edit location names and details</v-list-item-subtitle>
        <template #append>
          <v-icon>mdi-chevron-right</v-icon>
        </template>
      </v-list-item>

      <v-list-item
        to="/settings/payees"
        prepend-icon="mdi-account-cash"
      >
        <v-list-item-title>Manage Payees</v-list-item-title>
        <v-list-item-subtitle>Edit payee names and defaults</v-list-item-subtitle>
        <template #append>
          <v-icon>mdi-chevron-right</v-icon>
        </template>
      </v-list-item>

      <v-list-item
        to="/settings/start-fresh"
        prepend-icon="mdi-delete-sweep"
      >
        <v-list-item-title class="text-error">
          Start Fresh
        </v-list-item-title>
        <v-list-item-subtitle>Delete all or portions of your data</v-list-item-subtitle>
        <template #append>
          <v-icon>mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-list>

    <!-- Change Password Dialog -->
    <v-dialog
      v-model="showPasswordDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Change Password</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePassword">
            <v-text-field
              v-model="newPassword"
              label="New Password"
              type="password"
              :rules="[(v) => v.length >= 8 || 'Password must be at least 8 characters']"
              required
            />
            <v-text-field
              v-model="confirmPassword"
              label="Confirm Password"
              type="password"
              :rules="[(v) => v === newPassword || 'Passwords must match']"
              required
              class="mt-4"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showPasswordDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="savingPassword"
            @click="savePassword"
          >
            Update Password
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
