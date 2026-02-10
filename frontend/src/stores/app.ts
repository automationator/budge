import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getRegistrationStatus } from '@/api/public'

export const useAppStore = defineStore('app', () => {
  // State
  const registrationEnabled = ref<boolean | null>(null)
  const initialized = ref(false)

  // Actions
  async function initialize() {
    if (initialized.value) return

    try {
      const status = await getRegistrationStatus()
      registrationEnabled.value = status.registration_enabled
    } catch {
      // Default to true if we can't fetch (backend might not have the endpoint yet)
      registrationEnabled.value = true
    }

    initialized.value = true
  }

  async function refreshRegistrationStatus() {
    try {
      const status = await getRegistrationStatus()
      registrationEnabled.value = status.registration_enabled
    } catch {
      // Keep existing value on error
    }
  }

  return {
    // State
    registrationEnabled,
    initialized,
    // Actions
    initialize,
    refreshRegistrationStatus,
  }
})
