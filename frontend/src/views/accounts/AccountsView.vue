<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAccountsStore } from '@/stores/accounts'
import { useTransactionsStore } from '@/stores/transactions'
import { useEnvelopesStore } from '@/stores/envelopes'
import { showSnackbar } from '@/App.vue'
import AccountForm, { type FormData } from '@/components/accounts/AccountForm.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import type { Account, AccountType } from '@/types'

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

const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const envelopesStore = useEnvelopesStore()

const showCreateDialog = ref(false)
const creating = ref(false)

// Collapse states for sections
const budgetExpanded = ref(true)
const trackingExpanded = ref(true)

onMounted(async () => {
  try {
    await accountsStore.fetchAccounts()
  } catch {
    showSnackbar('Failed to load accounts', 'error')
  }
})

// Edit mode handlers
async function handleToggleEditMode() {
  if (!accountsStore.isEditMode) {
    // Entering edit mode - initialize sort orders if needed
    try {
      await accountsStore.initializeSortOrders()
    } catch {
      showSnackbar('Failed to initialize ordering', 'error')
      return
    }
  }
  accountsStore.toggleEditMode()
}

async function handleMoveAccountUp(accountId: string) {
  try {
    await accountsStore.moveAccountUp(accountId)
  } catch {
    showSnackbar('Failed to reorder account', 'error')
  }
}

async function handleMoveAccountDown(accountId: string) {
  try {
    await accountsStore.moveAccountDown(accountId)
  } catch {
    showSnackbar('Failed to reorder account', 'error')
  }
}

async function handleCreate(data: FormData) {
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
          date: new Date().toISOString().split('T')[0] ?? '',
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
  <div>
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <h1 class="text-h4">
        Accounts
      </h1>
      <v-spacer />
      <v-btn
        :variant="accountsStore.isEditMode ? 'tonal' : 'text'"
        :color="accountsStore.isEditMode ? 'primary' : undefined"
        :loading="accountsStore.reorderLoading"
        class="mr-2"
        data-testid="edit-order-button"
        @click="handleToggleEditMode"
      >
        <v-icon start>
          {{ accountsStore.isEditMode ? 'mdi-check' : 'mdi-pencil' }}
        </v-icon>
        {{ accountsStore.isEditMode ? 'Done' : 'Edit Order' }}
      </v-btn>
      <v-btn
        v-if="!accountsStore.isEditMode"
        color="primary"
        prepend-icon="mdi-plus"
        data-testid="add-account-button"
        @click="showCreateDialog = true"
      >
        Add Account
      </v-btn>
    </div>

    <!-- Loading State -->
    <div
      v-if="accountsStore.loading && accountsStore.accounts.length === 0"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <!-- Empty State -->
    <v-card v-else-if="accountsStore.accounts.length === 0">
      <v-card-text class="text-center text-grey py-8">
        <v-icon
          size="64"
          color="grey-lighten-1"
        >
          mdi-bank-off
        </v-icon>
        <p class="mt-4">
          No accounts yet. Add your first account to start tracking your finances!
        </p>
        <v-btn
          color="primary"
          class="mt-4"
          @click="showCreateDialog = true"
        >
          Add Account
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- Accounts List -->
    <v-card v-else>
      <v-list density="compact">
        <!-- All Accounts Link -->
        <v-list-item
          to="/transactions"
          prepend-icon="mdi-bank"
          data-testid="all-accounts-row"
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

        <v-divider class="my-2" />

        <!-- Budget Accounts Section -->
        <v-list-item
          data-testid="budget-section-header"
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

        <!-- Individual Budget Accounts -->
        <template v-if="budgetExpanded">
          <v-list-item
            v-for="(account, index) in accountsStore.budgetAccounts"
            :key="account.id"
            :to="accountsStore.isEditMode ? undefined : `/accounts/${account.id}`"
            class="pl-4"
            data-testid="budget-account-item"
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
              <div class="d-flex align-center gap-2">
                <!-- Edit mode: show reorder buttons -->
                <template v-if="accountsStore.isEditMode">
                  <v-btn
                    icon="mdi-chevron-up"
                    size="x-small"
                    variant="text"
                    data-testid="move-up-button"
                    :disabled="index === 0 || accountsStore.reorderLoading"
                    @click.prevent="handleMoveAccountUp(account.id)"
                  />
                  <v-btn
                    icon="mdi-chevron-down"
                    size="x-small"
                    variant="text"
                    data-testid="move-down-button"
                    :disabled="index === accountsStore.budgetAccounts.length - 1 || accountsStore.reorderLoading"
                    @click.prevent="handleMoveAccountDown(account.id)"
                  />
                </template>
                <!-- Normal mode: show balance -->
                <MoneyDisplay
                  v-else
                  :amount="account.cleared_balance + account.uncleared_balance"
                  size="small"
                />
              </div>
            </template>
          </v-list-item>
        </template>

        <!-- Tracking Accounts Section (only shown if there are tracking accounts) -->
        <template v-if="accountsStore.trackingAccounts.length > 0">
          <v-divider class="my-2" />

          <v-list-item
            data-testid="tracking-section-header"
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

          <!-- Individual Tracking Accounts -->
          <template v-if="trackingExpanded">
            <v-list-item
              v-for="(account, index) in accountsStore.trackingAccounts"
              :key="account.id"
              :to="accountsStore.isEditMode ? undefined : `/accounts/${account.id}`"
              class="pl-4"
              data-testid="tracking-account-item"
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
                <div class="d-flex align-center gap-2">
                  <!-- Edit mode: show reorder buttons -->
                  <template v-if="accountsStore.isEditMode">
                    <v-btn
                      icon="mdi-chevron-up"
                      size="x-small"
                      variant="text"
                      data-testid="move-up-button"
                      :disabled="index === 0 || accountsStore.reorderLoading"
                      @click.prevent="handleMoveAccountUp(account.id)"
                    />
                    <v-btn
                      icon="mdi-chevron-down"
                      size="x-small"
                      variant="text"
                      data-testid="move-down-button"
                      :disabled="index === accountsStore.trackingAccounts.length - 1 || accountsStore.reorderLoading"
                      @click.prevent="handleMoveAccountDown(account.id)"
                    />
                  </template>
                  <!-- Normal mode: show balance -->
                  <MoneyDisplay
                    v-else
                    :amount="account.cleared_balance + account.uncleared_balance"
                    size="small"
                  />
                </div>
              </template>
            </v-list-item>
          </template>
        </template>
      </v-list>
    </v-card>

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
            @submit="handleCreate"
            @cancel="showCreateDialog = false"
          />
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>
