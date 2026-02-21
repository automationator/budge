<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useNavDrawer } from '@/composables/useNavDrawer'
import { useAccountsStore } from '@/stores/accounts'
import { useEnvelopesStore } from '@/stores/envelopes'
import { useTransactionsStore } from '@/stores/transactions'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import AccountForm, { type FormData } from '@/components/accounts/AccountForm.vue'
import BudgetMenu from '@/components/layout/BudgetMenu.vue'
import type { Account, AccountType } from '@/types'
import { toLocaleDateString } from '@/utils/date'

function getAccountIcon(account: Account): string {
  if (account.icon) return account.icon
  const defaults: Record<AccountType, string> = {
    checking: 'mdi-bank',
    savings: 'mdi-piggy-bank',
    credit_card: 'mdi-credit-card',
    cash: 'mdi-cash',
    investment: 'mdi-chart-line',
    loan: 'mdi-hand-coin',
    other: 'mdi-wallet',
  }
  return defaults[account.account_type] || 'mdi-wallet'
}

function isEmoji(icon: string): boolean {
  return !icon.startsWith('mdi-')
}

const { mobile } = useDisplay()
const { isOpen } = useNavDrawer()
const accountsStore = useAccountsStore()
const envelopesStore = useEnvelopesStore()
const transactionsStore = useTransactionsStore()
const authStore = useAuthStore()

// Collapse states
const moreExpanded = ref(false)
const budgetExpanded = ref(true)
const trackingExpanded = ref(true)

// Create account dialog
const showCreateDialog = ref(false)
const creating = ref(false)

// Main nav items
const mainNavItems = [
  { title: 'Envelopes', icon: 'mdi-email-outline', to: '/' },
  { title: 'Transactions', icon: 'mdi-format-list-bulleted', to: '/transactions' },
  { title: 'Reports', icon: 'mdi-chart-bar', to: '/reports' },
]

// "More" section items
const moreNavItems = [
  { title: 'Allocation Rules', icon: 'mdi-tune-vertical', to: '/allocation-rules' },
  { title: 'Recurring Transactions', icon: 'mdi-repeat', to: '/recurring' },
]

onMounted(() => {
  if (authStore.currentBudgetId) {
    accountsStore.fetchAccounts()
  }
})

// Watch for budget changes to refetch accounts
watch(
  () => authStore.currentBudgetId,
  (budgetId) => {
    if (budgetId) {
      accountsStore.fetchAccounts()
    }
  }
)

async function handleCreateAccount(data: FormData) {
  try {
    creating.value = true
    const account = await accountsStore.createAccount(data)

    // If a starting balance was specified, create an adjustment transaction
    if (data.starting_balance && data.starting_balance !== 0) {
      try {
        // Load envelopes if not already loaded to get the unallocated envelope
        if (envelopesStore.envelopes.length === 0) {
          await envelopesStore.fetchEnvelopes()
        }

        const unallocatedEnvelope = envelopesStore.envelopes.find((e) => e.is_unallocated)

        await transactionsStore.createAdjustment({
          account_id: account.id,
          date: toLocaleDateString(),
          amount: data.starting_balance,
          is_cleared: true,
          memo: 'Starting balance',
          // Allocate to unallocated envelope so money shows up as available
          allocations: unallocatedEnvelope
            ? [{ envelope_id: unallocatedEnvelope.id, amount: data.starting_balance }]
            : undefined,
        })

        // Refresh account and envelopes to show updated balances
        await Promise.all([
          accountsStore.fetchAccount(account.id),
          envelopesStore.fetchEnvelopes(),
        ])
      } catch {
        // Account was created but adjustment failed - still show partial success
        showSnackbar('Account created, but failed to set starting balance', 'warning')
      }
    }

    // Close dialog AFTER everything completes (including starting balance)
    showCreateDialog.value = false
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to create account'
    showSnackbar(message, 'error')
  } finally {
    creating.value = false
  }
}

</script>

<template>
  <v-navigation-drawer
    v-if="!mobile"
    v-model="isOpen"
    :rail="false"
    :width="300"
    permanent
  >
    <!-- Budget Menu -->
    <BudgetMenu variant="sidebar" />

    <v-divider />

    <!-- Main Navigation -->
    <v-list
      nav
      density="compact"
    >
      <v-list-item
        v-for="item in mainNavItems"
        :key="item.to"
        :to="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        exact
      />

      <!-- Collapsible "More" Section -->
      <v-list-group v-model="moreExpanded">
        <template #activator="{ props }">
          <v-list-item
            v-bind="props"
            prepend-icon="mdi-dots-horizontal"
            title="More"
          />
        </template>
        <v-list-item
          v-for="item in moreNavItems"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          exact
        />
      </v-list-group>
    </v-list>

    <v-divider class="my-2" />

    <!-- Accounts Section -->
    <v-list density="compact">
      <!-- All Accounts Link -->
      <v-list-item
        to="/transactions"
        prepend-icon="mdi-bank"
        exact
      >
        <template #title>
          <span>All Accounts</span>
        </template>
        <template #append>
          <MoneyDisplay
            :amount="accountsStore.allAccountsTotalBalance"
            size="small"
          />
        </template>
      </v-list-item>

      <!-- Budget Accounts Section -->
      <v-list-item
        v-if="accountsStore.budgetAccounts.length > 0"
        @click="budgetExpanded = !budgetExpanded"
      >
        <template #title>
          <span>Budget</span>
        </template>
        <template #append>
          <MoneyDisplay
            :amount="accountsStore.budgetTotalBalance"
            size="small"
            class="mr-2"
          />
          <v-icon size="small">
            {{ budgetExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
          </v-icon>
        </template>
      </v-list-item>

      <!-- Individual Budget Accounts (shown when expanded) -->
      <template v-if="budgetExpanded && accountsStore.budgetAccounts.length > 0">
        <v-list-item
          v-for="account in accountsStore.budgetAccounts"
          :key="account.id"
          :to="`/accounts/${account.id}`"
          :ripple="false"
          exact
          class="pl-4"
        >
          <template #prepend>
            <span
              class="d-inline-flex justify-center"
              style="width: 24px;"
            >
              <span v-if="isEmoji(getAccountIcon(account))">{{ getAccountIcon(account) }}</span>
              <v-icon
                v-else
                size="small"
              >
                {{ getAccountIcon(account) }}
              </v-icon>
            </span>
          </template>
          <template #title>
            <span class="text-body-2">{{ account.name }}</span>
          </template>
          <template #append>
            <MoneyDisplay
              :amount="account.cleared_balance + account.uncleared_balance"
              size="small"
            />
          </template>
        </v-list-item>
      </template>

      <!-- Tracking Accounts Section -->
      <v-list-item
        v-if="accountsStore.trackingAccounts.length > 0"
        @click="trackingExpanded = !trackingExpanded"
      >
        <template #title>
          <span>Tracking</span>
        </template>
        <template #append>
          <MoneyDisplay
            :amount="accountsStore.trackingTotalBalance"
            size="small"
            class="mr-2"
          />
          <v-icon size="small">
            {{ trackingExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
          </v-icon>
        </template>
      </v-list-item>

      <!-- Individual Tracking Accounts (shown when expanded) -->
      <template v-if="trackingExpanded && accountsStore.trackingAccounts.length > 0">
        <v-list-item
          v-for="account in accountsStore.trackingAccounts"
          :key="account.id"
          :to="`/accounts/${account.id}`"
          :ripple="false"
          exact
          class="pl-4"
        >
          <template #prepend>
            <span
              class="d-inline-flex justify-center"
              style="width: 24px;"
            >
              <span v-if="isEmoji(getAccountIcon(account))">{{ getAccountIcon(account) }}</span>
              <v-icon
                v-else
                size="small"
              >
                {{ getAccountIcon(account) }}
              </v-icon>
            </span>
          </template>
          <template #title>
            <span class="text-body-2">{{ account.name }}</span>
          </template>
          <template #append>
            <MoneyDisplay
              :amount="account.cleared_balance + account.uncleared_balance"
              size="small"
            />
          </template>
        </v-list-item>
      </template>
    </v-list>

    <!-- Add Account Button (at bottom) -->
    <template #append>
      <div class="pa-2">
        <v-btn
          variant="text"
          block
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
        >
          Add Account
        </v-btn>
      </div>
    </template>
  </v-navigation-drawer>

  <!-- Create Account Dialog -->
  <v-dialog
    v-model="showCreateDialog"
    max-width="500"
  >
    <v-card>
      <v-card-title>Create Account</v-card-title>
      <v-card-text>
        <AccountForm
          :loading="creating"
          @submit="handleCreateAccount"
          @cancel="showCreateDialog = false"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
