<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { useAccountsStore } from '@/stores/accounts'
import { useEnvelopesStore } from '@/stores/envelopes'
import { usePayeesStore } from '@/stores/payees'
import { showSnackbar } from '@/App.vue'
import AccountForm, { type FormData } from '@/components/accounts/AccountForm.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import TransactionList from '@/components/transactions/TransactionList.vue'
import TransactionFormDialog from '@/components/transactions/TransactionFormDialog.vue'
import UpcomingTransactionsSection from '@/components/transactions/UpcomingTransactionsSection.vue'
import { parseMoney } from '@/utils/money'
import { listTransactions } from '@/api/transactions'
import { useAuthStore } from '@/stores/auth'
import type { Transaction } from '@/types'
import { showEnvelopeBalanceToast } from '@/composables/useTransactionToast'

const route = useRoute()
const router = useRouter()
const { mobile } = useDisplay()
const authStore = useAuthStore()
const accountsStore = useAccountsStore()
const envelopesStore = useEnvelopesStore()
const payeesStore = usePayeesStore()

const accountId = computed(() => route.params.id as string)
const account = computed(() => accountsStore.getAccountById(accountId.value))
const workingBalance = computed(() =>
  account.value ? account.value.cleared_balance + account.value.uncleared_balance : 0
)

const loading = ref(true)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showReconcileDialog = ref(false)
const hideReconciled = ref(false)
const saving = ref(false)

// Transaction dialog state
const showTransactionDialog = ref(false)
const editingTransactionId = ref<string | null>(null)

const reconcileStep = ref<1 | 2>(1)
const reconcileBalance = ref('')
const reconcileBalanceIsNegative = ref(false)

// Transaction list state
const transactions = ref<Transaction[]>([])
const transactionsLoading = ref(false)
const transactionsCursor = ref<string | null>(null)
const transactionsHasMore = ref(false)

// Upcoming transactions state
const upcomingTransactions = ref<Transaction[]>([])
const upcomingLoading = ref(false)

async function fetchAccountTransactions(reset = false) {
  if (!authStore.currentBudgetId) return

  if (reset) {
    transactions.value = []
    transactionsCursor.value = null
  }

  try {
    transactionsLoading.value = true
    const response = await listTransactions(authStore.currentBudgetId, {
      account_id: accountId.value,
      cursor: transactionsCursor.value,
      limit: 50,
      is_reconciled: hideReconciled.value ? false : undefined,
      // Exclude scheduled transactions - they appear in Upcoming section
      include_scheduled: false,
    })

    if (reset) {
      transactions.value = response.items
    } else {
      transactions.value = [...transactions.value, ...response.items]
    }

    transactionsCursor.value = response.next_cursor
    transactionsHasMore.value = response.has_more
  } catch {
    showSnackbar('Failed to load transactions', 'error')
  } finally {
    transactionsLoading.value = false
  }
}

async function fetchUpcomingTransactions() {
  if (!authStore.currentBudgetId) return

  try {
    upcomingLoading.value = true
    const response = await listTransactions(authStore.currentBudgetId, {
      account_id: accountId.value,
      status: ['scheduled'],
      limit: 30,
    })
    upcomingTransactions.value = response.items
  } catch {
    // Silently fail - upcoming section is optional
  } finally {
    upcomingLoading.value = false
  }
}

async function handleFilter() {
  await fetchAccountTransactions(true)
}

function openNewTransaction() {
  editingTransactionId.value = null
  showTransactionDialog.value = true
}

function openEditTransaction(transactionId: string) {
  editingTransactionId.value = transactionId
  showTransactionDialog.value = true
}

onMounted(async () => {
  try {
    // Load account, transactions, and payees in parallel
    await Promise.all([
      accountsStore.fetchAccount(accountId.value),
      fetchAccountTransactions(true),
      fetchUpcomingTransactions(),
      payeesStore.fetchPayees(),
    ])
  } catch {
    showSnackbar('Failed to load account', 'error')
    router.push('/accounts')
  } finally {
    loading.value = false
  }
})

watch(accountId, async (newId, oldId) => {
  if (newId === oldId) return
  loading.value = true
  try {
    await Promise.all([
      accountsStore.fetchAccount(newId),
      fetchAccountTransactions(true),
      fetchUpcomingTransactions(),
    ])
  } catch {
    showSnackbar('Failed to load account', 'error')
    router.push('/accounts')
  } finally {
    loading.value = false
  }
})

const accountTypeLabel = computed(() => {
  if (!account.value) return ''
  switch (account.value.account_type) {
    case 'checking':
      return 'Checking'
    case 'savings':
      return 'Savings'
    case 'credit_card':
      return 'Credit Card'
    case 'cash':
      return 'Cash'
    case 'investment':
      return 'Investment'
    case 'loan':
      return 'Loan'
    default:
      return 'Other'
  }
})

const accountIcon = computed(() => {
  if (!account.value) return 'mdi-wallet'
  if (account.value.icon) return account.value.icon
  switch (account.value.account_type) {
    case 'checking':
      return 'mdi-bank'
    case 'savings':
      return 'mdi-piggy-bank'
    case 'credit_card':
      return 'mdi-credit-card'
    case 'cash':
      return 'mdi-cash'
    case 'investment':
      return 'mdi-chart-line'
    case 'loan':
      return 'mdi-hand-coin'
    default:
      return 'mdi-wallet'
  }
})

const isAccountIconEmoji = computed(() => {
  // MDI icons start with 'mdi-', everything else is treated as emoji
  return accountIcon.value && !accountIcon.value.startsWith('mdi-')
})

const reconciliationStatus = computed(() => {
  if (!account.value?.last_reconciled_at) {
    return { message: 'Never reconciled', needsReconciliation: true }
  }

  const lastReconciled = new Date(account.value.last_reconciled_at)
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

  if (diffDays <= 0) {
    return { message: 'Last reconciled today', needsReconciliation: false }
  } else if (diffDays === 1) {
    return { message: 'Last reconciled yesterday', needsReconciliation: false }
  } else if (diffDays > 30) {
    return { message: `Last reconciled ${diffDays} days ago`, needsReconciliation: true }
  } else {
    return { message: `Last reconciled ${diffDays} days ago`, needsReconciliation: false }
  }
})

async function handleEdit(data: FormData) {
  try {
    saving.value = true
    await accountsStore.updateAccount(accountId.value, data)
    showEditDialog.value = false
  } catch {
    showSnackbar('Failed to update account', 'error')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  try {
    saving.value = true
    await accountsStore.deleteAccount(accountId.value)

    // Refresh envelopes since deleting an account also deletes its allocations
    await envelopesStore.fetchEnvelopes()

    router.push('/accounts')
  } catch {
    showSnackbar('Failed to delete account', 'error')
  } finally {
    saving.value = false
    showDeleteDialog.value = false
  }
}

function openReconcileDialog() {
  if (account.value) {
    reconcileBalanceIsNegative.value = account.value.cleared_balance < 0
    reconcileBalance.value = (Math.abs(account.value.cleared_balance) / 100).toFixed(2)
  }
  reconcileStep.value = 1
  showReconcileDialog.value = true
}

async function handleReconcileConfirmBalance() {
  // User confirmed balance is correct - reconcile with current cleared balance
  try {
    saving.value = true
    await accountsStore.reconcileAccount(accountId.value, account.value!.cleared_balance)

    // Refresh envelopes and transactions to reflect changes
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      fetchAccountTransactions(true),
    ])

    showReconcileDialog.value = false
  } catch {
    showSnackbar('Failed to reconcile account', 'error')
  } finally {
    saving.value = false
  }
}

function handleReconcileNeedAdjustment() {
  reconcileStep.value = 2
}

async function handleReconcile() {
  try {
    saving.value = true
    const parsedBalance = parseMoney(reconcileBalance.value)
    const actualBalance = reconcileBalanceIsNegative.value ? -parsedBalance : parsedBalance
    await accountsStore.reconcileAccount(accountId.value, actualBalance)

    // Refresh envelopes and transactions to reflect the adjustment
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      fetchAccountTransactions(true),
    ])

    showReconcileDialog.value = false
  } catch {
    showSnackbar('Failed to reconcile account', 'error')
  } finally {
    saving.value = false
  }
}

async function handleTransactionCreated(transaction: Transaction) {
  await handleTransactionChange()
  await showEnvelopeBalanceToast(transaction)
}

async function handleTransactionChange() {
  // Refresh account balance and transactions
  await Promise.all([
    accountsStore.fetchAccount(accountId.value),
    fetchAccountTransactions(true),
    fetchUpcomingTransactions(),
    envelopesStore.fetchEnvelopes(),
  ])
}
</script>

<template>
  <div>
    <v-btn
      variant="text"
      to="/accounts"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
    >
      Back to Accounts
    </v-btn>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <template v-else-if="account">
      <!-- Account Header -->
      <v-card class="mb-4">
        <v-card-item>
          <template #prepend>
            <v-avatar
              color="primary"
              size="48"
            >
              <span
                v-if="isAccountIconEmoji"
                class="text-h5"
              >{{ accountIcon }}</span>
              <v-icon
                v-else
                size="28"
              >
                {{ accountIcon }}
              </v-icon>
            </v-avatar>
          </template>

          <v-card-title class="text-h5">
            {{ account.name }}
          </v-card-title>
          <v-card-subtitle>{{ accountTypeLabel }}</v-card-subtitle>

          <!-- Desktop: Balance in append slot -->
          <template #append>
            <div class="text-right d-none d-sm-block">
              <div class="d-flex align-center justify-end ga-3">
                <!-- Cleared Balance -->
                <div class="text-center">
                  <MoneyDisplay
                    :amount="account.cleared_balance"
                    size="medium"
                    class="text-success"
                    :colored="false"
                  />
                  <div class="text-caption text-grey">
                    Cleared
                  </div>
                </div>
                <span class="text-grey text-h6">+</span>
                <!-- Uncleared Balance -->
                <div class="text-center">
                  <MoneyDisplay
                    :amount="account.uncleared_balance"
                    size="medium"
                    class="text-warning"
                    :colored="false"
                  />
                  <div class="text-caption text-grey">
                    Uncleared
                  </div>
                </div>
                <span class="text-grey text-h6">=</span>
                <!-- Working Balance -->
                <div class="text-center">
                  <MoneyDisplay
                    :amount="workingBalance"
                    size="large"
                  />
                  <div class="text-caption text-grey">
                    Working
                  </div>
                </div>
              </div>
              <div
                v-if="!account.include_in_budget"
                class="text-caption text-grey mt-1"
              >
                Off-budget
              </div>
            </div>
          </template>
        </v-card-item>

        <!-- Mobile: Balance below header -->
        <v-card-text class="d-block d-sm-none pt-0 pb-2">
          <div class="d-flex justify-space-between align-center">
            <div>
              <MoneyDisplay
                :amount="workingBalance"
                size="large"
              />
              <div class="text-caption text-medium-emphasis">
                Working Balance
              </div>
            </div>
            <div class="text-right text-caption text-medium-emphasis">
              <div>
                Cleared: <MoneyDisplay
                  :amount="account.cleared_balance"
                  size="small"
                  :colored="false"
                  class="d-inline text-success"
                />
              </div>
              <div>
                Uncleared: <MoneyDisplay
                  :amount="account.uncleared_balance"
                  size="small"
                  :colored="false"
                  class="d-inline text-warning"
                />
              </div>
              <div
                v-if="!account.include_in_budget"
                class="text-grey"
              >
                Off-budget
              </div>
            </div>
          </div>
        </v-card-text>

        <v-card-text v-if="account.description">
          {{ account.description }}
        </v-card-text>

        <v-card-actions class="flex-wrap ga-1">
          <v-btn
            variant="text"
            :icon="mobile"
            :prepend-icon="mobile ? undefined : 'mdi-pencil'"
            @click="showEditDialog = true"
          >
            <v-icon v-if="mobile">
              mdi-pencil
            </v-icon>
            <span v-else>Edit</span>
          </v-btn>
          <v-btn
            variant="text"
            :icon="mobile"
            :prepend-icon="mobile ? undefined : 'mdi-scale-balance'"
            @click="openReconcileDialog"
          >
            <v-icon v-if="mobile">
              mdi-scale-balance
            </v-icon>
            <span v-else>Reconcile</span>
          </v-btn>
          <span
            class="text-caption ml-2 d-none d-sm-inline"
            :class="reconciliationStatus.needsReconciliation ? 'text-warning' : 'text-medium-emphasis'"
            data-testid="last-reconciled-text"
          >
            {{ reconciliationStatus.message }}
          </span>
          <v-spacer />
          <v-btn
            variant="text"
            color="error"
            :icon="mobile"
            :prepend-icon="mobile ? undefined : 'mdi-delete'"
            @click="showDeleteDialog = true"
          >
            <v-icon v-if="mobile">
              mdi-delete
            </v-icon>
            <span v-else>Delete</span>
          </v-btn>
        </v-card-actions>
      </v-card>

      <!-- Upcoming Transactions Section -->
      <UpcomingTransactionsSection
        :transactions="upcomingTransactions"
        :loading="upcomingLoading"
        :storage-key="`budge:account:${accountId}:upcoming-collapsed`"
        hide-account-name
        @transaction-click="openEditTransaction"
      />

      <!-- Transactions Toolbar -->
      <div class="d-flex align-center ga-2 mb-3">
        <v-chip
          :color="hideReconciled ? 'success' : 'default'"
          :variant="hideReconciled ? 'elevated' : 'outlined'"
          size="small"
          @click="hideReconciled = !hideReconciled; handleFilter()"
        >
          <v-icon
            start
            size="small"
          >
            mdi-check-circle-outline
          </v-icon>
          <span class="d-none d-sm-inline">Hide Reconciled</span>
          <span class="d-inline d-sm-none">Hide</span>
        </v-chip>
        <v-spacer />
        <v-btn
          color="primary"
          :icon="mobile"
          :prepend-icon="mobile ? undefined : 'mdi-plus'"
          @click="openNewTransaction"
        >
          <v-icon v-if="mobile">
            mdi-plus
          </v-icon>
          <span v-else>Add Transaction</span>
        </v-btn>
      </div>

      <!-- Transaction List -->
      <TransactionList
        :transactions="transactions"
        :loading="transactionsLoading"
        :has-more="transactionsHasMore"
        hide-account-name
        empty-icon="mdi-receipt-text-outline"
        @transaction-click="openEditTransaction"
        @load-more="fetchAccountTransactions()"
      />
    </template>

    <!-- Edit Dialog -->
    <v-dialog
      v-model="showEditDialog"
      max-width="500"
    >
      <v-card>
        <v-card-title>Edit Account</v-card-title>
        <v-card-text>
          <AccountForm
            :account="account"
            :loading="saving"
            @submit="handleEdit"
            @cancel="showEditDialog = false"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Delete Account?</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ account?.name }}"?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="saving"
            @click="handleDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reconcile Dialog -->
    <v-dialog
      v-model="showReconcileDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Reconcile Account</v-card-title>

        <!-- Step 1: Confirmation -->
        <template v-if="reconcileStep === 1">
          <v-card-text>
            <p class="mb-4">
              Is this balance correct according to your bank statement?
            </p>
            <div class="text-center py-4">
              <MoneyDisplay
                :amount="account!.cleared_balance"
                size="large"
              />
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              variant="text"
              @click="showReconcileDialog = false"
            >
              Cancel
            </v-btn>
            <v-btn
              variant="text"
              @click="handleReconcileNeedAdjustment"
            >
              No
            </v-btn>
            <v-btn
              color="primary"
              :loading="saving"
              @click="handleReconcileConfirmBalance"
            >
              Yes
            </v-btn>
          </v-card-actions>
        </template>

        <!-- Step 2: Balance Entry -->
        <template v-if="reconcileStep === 2">
          <v-card-text>
            <p class="mb-4">
              Enter the actual balance from your bank statement.
              An adjustment transaction will be created for any difference.
            </p>
            <MoneyInput
              v-model="reconcileBalance"
              v-model:is-expense="reconcileBalanceIsNegative"
              label="Actual Balance"
              :required="false"
              autofocus
            />
          </v-card-text>
          <v-card-actions>
            <v-btn
              variant="text"
              @click="reconcileStep = 1"
            >
              Back
            </v-btn>
            <v-spacer />
            <v-btn
              variant="text"
              @click="showReconcileDialog = false"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              :loading="saving"
              @click="handleReconcile"
            >
              Reconcile
            </v-btn>
          </v-card-actions>
        </template>
      </v-card>
    </v-dialog>

    <!-- Transaction Form Dialog -->
    <TransactionFormDialog
      v-model="showTransactionDialog"
      :account-id="accountId"
      :transaction-id="editingTransactionId"
      @created="handleTransactionCreated"
      @updated="handleTransactionChange"
      @deleted="handleTransactionChange"
    />
  </div>
</template>
