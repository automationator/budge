<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import { useEnvelopesStore } from '@/stores/envelopes'
import AppBar from '@/components/layout/AppBar.vue'
import NavDrawer from '@/components/layout/NavDrawer.vue'
import BottomNav from '@/components/layout/BottomNav.vue'
import TransactionFormDialog from '@/components/transactions/TransactionFormDialog.vue'
import { snackbar, snackbarTrigger, SNACKBAR_TIMEOUT } from '@/composables/useSnackbar'
import {
  showTransactionDialog,
  editingTransactionId,
  preselectedAccountId,
  preselectedEnvelopeId,
  notifyTransactionChange,
} from '@/composables/useGlobalTransactionDialog'
import { showEnvelopeBalanceToast } from '@/composables/useTransactionToast'
import type { Transaction } from '@/types'

const route = useRoute()
const authStore = useAuthStore()
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const envelopesStore = useEnvelopesStore()

const isAuthLayout = computed(() => route.meta.layout === 'auth')

// Handler for when a transaction is created via global dialog
async function handleTransactionCreated(transaction: Transaction) {
  await handleTransactionChange()
  await showEnvelopeBalanceToast(transaction)
}

// Handler for when a transaction is created/updated/deleted via global dialog
async function handleTransactionChange() {
  // Refresh relevant stores
  await Promise.all([
    transactionsStore.fetchTransactions(true),
    transactionsStore.fetchUnallocatedCount(),
    accountsStore.fetchAccounts(),
    envelopesStore.fetchEnvelopes(),
    envelopesStore.fetchBudgetSummary(),
  ])
  // Notify any listeners (e.g., views that need to refresh their local data)
  notifyTransactionChange()
}

const showNav = computed(() => authStore.isAuthenticated && !isAuthLayout.value)

// Track timeout and animation for cleanup
let currentTimeoutId: number | null = null
let animationRunning = false

// Countdown animation for snackbar dismiss indicator
function startCountdown() {
  // Clear any existing timeout
  if (currentTimeoutId) {
    window.clearTimeout(currentTimeoutId)
  }

  const startTime = Date.now()
  snackbar.progress = 100
  animationRunning = true

  // Auto-close after timeout (managed ourselves for perfect sync with progress)
  currentTimeoutId = window.setTimeout(() => {
    snackbar.show = false
    currentTimeoutId = null
  }, SNACKBAR_TIMEOUT)

  const animate = () => {
    if (!animationRunning) return

    const elapsed = Date.now() - startTime
    snackbar.progress = Math.max(0, 100 - (elapsed / SNACKBAR_TIMEOUT) * 100)

    if (snackbar.show && snackbar.progress > 0) {
      window.requestAnimationFrame(animate)
    }
  }
  window.requestAnimationFrame(animate)
}

// Watch for snackbar trigger changes (increments each time showSnackbar is called)
watch(() => snackbarTrigger.value, () => {
  if (snackbar.show) {
    startCountdown()
  }
})

// Watch for manual close
watch(() => snackbar.show, (isVisible) => {
  if (!isVisible) {
    snackbar.progress = 100
    animationRunning = false
    if (currentTimeoutId) {
      window.clearTimeout(currentTimeoutId)
      currentTimeoutId = null
    }
  }
})
</script>

<template>
  <v-app>
    <!-- Auth layout (login/register) -->
    <template v-if="isAuthLayout">
      <v-main>
        <router-view />
      </v-main>
    </template>

    <!-- Main app layout -->
    <template v-else>
      <AppBar v-if="showNav" />
      <NavDrawer v-if="showNav" />

      <v-main>
        <v-container
          fluid
          class="pa-4"
        >
          <router-view />
        </v-container>
      </v-main>

      <BottomNav v-if="showNav" />

      <!-- Global Transaction Form Dialog -->
      <TransactionFormDialog
        v-if="showNav"
        v-model="showTransactionDialog"
        :account-id="preselectedAccountId"
        :envelope-id="preselectedEnvelopeId"
        :transaction-id="editingTransactionId"
        @created="handleTransactionCreated"
        @updated="handleTransactionChange"
        @deleted="handleTransactionChange"
      />
    </template>

    <!-- Global snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="-1"
      location="top"
    >
      {{ snackbar.message }}
      <template #actions>
        <div
          class="snackbar-close-btn"
          @click="snackbar.show = false"
        >
          <v-progress-circular
            :model-value="snackbar.progress"
            :size="28"
            :width="2"
            color="white"
          >
            <v-icon size="small">
              mdi-close
            </v-icon>
          </v-progress-circular>
        </div>
      </template>
    </v-snackbar>
  </v-app>
</template>

<!-- Re-export snackbar utilities for backwards compatibility -->
<script lang="ts">
export { showSnackbar, snackbar, snackbarTrigger, SNACKBAR_TIMEOUT } from '@/composables/useSnackbar'
</script>

<style>
/* Remove default margins */
html, body {
  margin: 0;
  padding: 0;
}

/* Adjust main content for bottom nav on mobile */
@media (max-width: 960px) {
  .v-application .v-main .v-container {
    padding-bottom: calc(84px + env(safe-area-inset-bottom)) !important;  /* 56px nav + 12px gap + 16px buffer + safe area */
  }
}

/* Modern form field styling */
.v-field--variant-solo-filled {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px !important;
  background: rgba(var(--v-theme-on-surface), 0.04) !important;
}

/* Uniform form field spacing */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Gradient primary action button */
.create-btn:not(.v-btn--disabled) {
  background: linear-gradient(135deg, #7c83ff, #6c5ce7) !important;
  box-shadow: 0 2px 12px rgba(124, 131, 255, 0.2) !important;
}
.create-btn:not(.v-btn--disabled):hover {
  box-shadow: 0 4px 16px rgba(124, 131, 255, 0.3) !important;
}

/* Snackbar close button with countdown ring */
.snackbar-close-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
}

/* Disable Vuetify's transition on the progress circle so it updates instantly */
.snackbar-close-btn .v-progress-circular__overlay {
  transition: none !important;
}
</style>
