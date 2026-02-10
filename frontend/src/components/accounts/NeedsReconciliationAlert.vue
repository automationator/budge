<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore } from '@/stores/accounts'

const RECONCILIATION_THRESHOLD_DAYS = 30

const router = useRouter()
const accountsStore = useAccountsStore()

const accountsNeedingReconciliation = computed(() => {
  return accountsStore.activeAccounts.filter((account) => {
    if (!account.last_reconciled_at) return true

    const lastReconciled = new Date(account.last_reconciled_at)
    const now = new Date()

    // Use date-only comparison to avoid timezone issues
    const lastReconciledDate = new Date(
      lastReconciled.getFullYear(),
      lastReconciled.getMonth(),
      lastReconciled.getDate()
    )
    const todayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const diffMs = todayDate.getTime() - lastReconciledDate.getTime()
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))

    return diffDays > RECONCILIATION_THRESHOLD_DAYS
  })
})

const hasAccountsNeedingReconciliation = computed(
  () => accountsNeedingReconciliation.value.length > 0
)

function getDaysMessage(lastReconciledAt: string | null): string {
  if (!lastReconciledAt) return 'Never'

  const lastReconciled = new Date(lastReconciledAt)
  const now = new Date()

  // Use date-only comparison to avoid timezone issues
  const lastReconciledDate = new Date(
    lastReconciled.getFullYear(),
    lastReconciled.getMonth(),
    lastReconciled.getDate()
  )
  const todayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffMs = todayDate.getTime() - lastReconciledDate.getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))

  return `${diffDays} days ago`
}

function navigateToAccount(accountId: string) {
  router.push(`/accounts/${accountId}`)
}
</script>

<template>
  <v-alert
    v-if="hasAccountsNeedingReconciliation"
    type="info"
    variant="tonal"
    prominent
    class="mb-4"
    data-testid="needs-reconciliation-alert"
  >
    <template #title>
      Accounts Need Reconciliation
    </template>

    <div class="mb-3">
      The following accounts haven't been reconciled in over 30 days. Reconciling ensures your
      records match your bank statements.
    </div>

    <div class="d-flex flex-column gap-1 mb-3">
      <div
        v-for="account in accountsNeedingReconciliation"
        :key="account.id"
        class="d-flex justify-space-between align-center"
      >
        <span>{{ account.name }}</span>
        <v-btn
          size="small"
          variant="text"
          color="primary"
          @click="navigateToAccount(account.id)"
        >
          {{ getDaysMessage(account.last_reconciled_at) }}
        </v-btn>
      </div>
    </div>
  </v-alert>
</template>
