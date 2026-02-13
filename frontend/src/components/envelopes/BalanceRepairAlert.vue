<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

defineProps<{
  needsRepair: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'repair'): void
}>()

const authStore = useAuthStore()

const isOwner = computed(() => {
  return authStore.currentBudget?.owner_id === authStore.user?.id
})
</script>

<template>
  <v-alert
    v-if="needsRepair"
    type="error"
    variant="tonal"
    prominent
    class="mb-4"
    data-testid="balance-repair-alert"
  >
    <template #title>
      Balance Mismatch Detected
    </template>

    <div class="mb-3">
      Some account or envelope balances are out of sync with their transactions.
      This can happen due to a previous bug and can be fixed automatically.
    </div>

    <v-btn
      v-if="isOwner"
      color="error"
      variant="flat"
      :loading="loading"
      @click="emit('repair')"
    >
      Repair Balances
    </v-btn>
    <div
      v-else
      class="text-body-2 text-medium-emphasis"
    >
      Ask the budget owner to repair balances in Budget Settings.
    </div>
  </v-alert>
</template>
