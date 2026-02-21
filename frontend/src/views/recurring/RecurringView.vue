<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRecurringStore } from '@/stores/recurring'
import { useAccountsStore } from '@/stores/accounts'
import { usePayeesStore } from '@/stores/payees'
import { useEnvelopesStore } from '@/stores/envelopes'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import AccountSelect from '@/components/common/AccountSelect.vue'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import PayeeSelect from '@/components/common/PayeeSelect.vue'
import type { RecurringTransaction, FrequencyUnit } from '@/types'
import { toLocaleDateString } from '@/utils/date'

const recurringStore = useRecurringStore()
const accountsStore = useAccountsStore()
const payeesStore = usePayeesStore()
const envelopesStore = useEnvelopesStore()

const showInactive = ref(false)

// Form dialog state
const showFormDialog = ref(false)
const editingId = ref<string | null>(null)
const formLoading = ref(false)

// Form fields
const formAccountId = ref<string | null>(null)
const formDestinationAccountId = ref<string | null>(null)
const formPayeeId = ref<string | null>(null)
const formEnvelopeId = ref<string | null>(null)
const formAmount = ref('')
const formIsExpense = ref(true)
const formFrequencyValue = ref('1')
const formFrequencyUnit = ref<FrequencyUnit>('months')
const formStartDate = ref(toLocaleDateString())
const formEndDate = ref('')
const formMemo = ref('')
const formIsTransfer = ref(false)

// Delete dialog
const showDeleteDialog = ref(false)
const deletingId = ref<string | null>(null)
const deleting = ref(false)
const deleteScheduled = ref(true)

onMounted(async () => {
  try {
    await Promise.all([
      recurringStore.fetchRecurringTransactions(showInactive.value),
      accountsStore.fetchAccounts(),
      payeesStore.fetchPayees(),
      envelopesStore.fetchEnvelopes(),
    ])
  } catch {
    showSnackbar('Failed to load recurring transactions', 'error')
  }
})

const displayedRecurring = computed(() => {
  if (showInactive.value) {
    return recurringStore.recurringTransactions
  }
  return recurringStore.activeRecurring
})

const sortedRecurring = computed(() => {
  return [...displayedRecurring.value].sort((a, b) => {
    const aDate = a.next_scheduled_date || a.next_occurrence_date
    const bDate = b.next_scheduled_date || b.next_occurrence_date
    return aDate.localeCompare(bDate)
  })
})

const isInBudgetAccount = computed(() => {
  if (!formAccountId.value) return false
  const account = accountsStore.accounts.find((a) => a.id === formAccountId.value)
  return account?.include_in_budget ?? false
})

// Check if destination account is a tracking (non-budget) account
const isDestinationTrackingAccount = computed(() => {
  if (!formDestinationAccountId.value) return false
  const account = accountsStore.accounts.find((a) => a.id === formDestinationAccountId.value)
  return account?.include_in_budget === false
})

// Check if transfer is from budget account to tracking account (money leaving budget)
const isBudgetToTrackingTransfer = computed(() => {
  if (!formIsTransfer.value) return false
  return isInBudgetAccount.value && isDestinationTrackingAccount.value
})

// Envelope is required for expenses in budget accounts
const isEnvelopeRequired = computed(() => {
  return isInBudgetAccount.value && formIsExpense.value && !formIsTransfer.value
})

const required = [(v: unknown) => !!v || 'Required']

const frequencyUnitOptions = [
  { title: 'Day(s)', value: 'days' },
  { title: 'Week(s)', value: 'weeks' },
  { title: 'Month(s)', value: 'months' },
  { title: 'Year(s)', value: 'years' },
]

function getAccountName(id: string | null): string {
  if (!id) return 'Unknown'
  return accountsStore.getAccountById(id)?.name || 'Unknown'
}

function getPayeeName(id: string | null): string {
  if (!id) return ''
  return payeesStore.getPayeeById(id)?.name || 'Unknown'
}

function getEnvelopeName(id: string | null): string {
  if (!id) return ''
  return envelopesStore.getEnvelopeById(id)?.name || ''
}

function formatFrequency(r: RecurringTransaction): string {
  const value = r.frequency_value
  const unit = r.frequency_unit
  if (value === 1) {
    switch (unit) {
      case 'days':
        return 'Daily'
      case 'weeks':
        return 'Weekly'
      case 'months':
        return 'Monthly'
      case 'years':
        return 'Yearly'
    }
  }
  return `Every ${value} ${unit}`
}

function formatNextDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const diffDays = Math.floor((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays < 7) return `In ${diffDays} days`

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function isTransfer(r: RecurringTransaction): boolean {
  return !!r.destination_account_id
}

function getDisplayName(r: RecurringTransaction): string {
  if (isTransfer(r)) {
    return `Transfer to ${getAccountName(r.destination_account_id)}`
  }
  return getPayeeName(r.payee_id) || 'Unknown'
}

function getIcon(r: RecurringTransaction): string {
  if (isTransfer(r)) return 'mdi-swap-horizontal'
  if (r.amount > 0) return 'mdi-arrow-down'
  return 'mdi-arrow-up'
}

function getIconColor(r: RecurringTransaction): string {
  if (isTransfer(r)) return 'info'
  if (r.amount > 0) return 'success'
  return 'error'
}

function openCreateDialog() {
  editingId.value = null
  formAccountId.value = null
  formDestinationAccountId.value = null
  formPayeeId.value = null
  formEnvelopeId.value = null
  formAmount.value = ''
  formIsExpense.value = true
  formFrequencyValue.value = '1'
  formFrequencyUnit.value = 'months'
  formStartDate.value = toLocaleDateString()
  formEndDate.value = ''
  formMemo.value = ''
  formIsTransfer.value = false
  showFormDialog.value = true
}

function openEditDialog(r: RecurringTransaction) {
  editingId.value = r.id
  formAccountId.value = r.account_id
  formDestinationAccountId.value = r.destination_account_id
  formPayeeId.value = r.payee_id
  formEnvelopeId.value = r.envelope_id
  formAmount.value = (Math.abs(r.amount) / 100).toFixed(2)
  formIsExpense.value = r.amount < 0
  formFrequencyValue.value = r.frequency_value.toString()
  formFrequencyUnit.value = r.frequency_unit
  formStartDate.value = r.start_date
  formEndDate.value = r.end_date || ''
  formMemo.value = r.memo || ''
  formIsTransfer.value = !!r.destination_account_id
  showFormDialog.value = true
}

async function handleSubmit() {
  if (!formAccountId.value) return

  const amountCents = Math.round(parseFloat(formAmount.value) * 100)
  if (amountCents <= 0) {
    showSnackbar('Amount must be greater than 0', 'error')
    return
  }

  const amount = formIsTransfer.value
    ? -amountCents // Transfers are always negative from source
    : formIsExpense.value
      ? -amountCents
      : amountCents

  try {
    formLoading.value = true

    if (editingId.value) {
      await recurringStore.updateRecurringTransaction(editingId.value, {
        account_id: formAccountId.value,
        destination_account_id: formIsTransfer.value ? formDestinationAccountId.value : null,
        payee_id: formIsTransfer.value ? null : formPayeeId.value,
        envelope_id: formEnvelopeId.value,
        amount,
        frequency_value: parseInt(formFrequencyValue.value),
        frequency_unit: formFrequencyUnit.value,
        start_date: formStartDate.value,
        end_date: formEndDate.value.trim() || null,
        memo: formMemo.value.trim() || null,
      })
    } else {
      await recurringStore.createRecurringTransaction({
        account_id: formAccountId.value,
        destination_account_id: formIsTransfer.value ? formDestinationAccountId.value : null,
        payee_id: formIsTransfer.value ? null : formPayeeId.value,
        envelope_id: formEnvelopeId.value,
        amount,
        frequency_value: parseInt(formFrequencyValue.value),
        frequency_unit: formFrequencyUnit.value,
        start_date: formStartDate.value,
        end_date: formEndDate.value.trim() || null,
        memo: formMemo.value.trim() || null,
      })
    }

    showFormDialog.value = false
  } catch {
    showSnackbar('Failed to save recurring transaction', 'error')
  } finally {
    formLoading.value = false
  }
}

function openDeleteDialog(r: RecurringTransaction) {
  deletingId.value = r.id
  deleteScheduled.value = true
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deletingId.value) return

  try {
    deleting.value = true
    await recurringStore.deleteRecurringTransaction(deletingId.value, deleteScheduled.value)
    showDeleteDialog.value = false
  } catch {
    showSnackbar('Failed to delete recurring transaction', 'error')
  } finally {
    deleting.value = false
  }
}

async function toggleActive(r: RecurringTransaction) {
  try {
    await recurringStore.updateRecurringTransaction(r.id, {
      is_active: !r.is_active,
    })
  } catch {
    showSnackbar('Failed to update', 'error')
  }
}

async function handleShowInactiveChange() {
  try {
    await recurringStore.fetchRecurringTransactions(showInactive.value)
  } catch {
    showSnackbar('Failed to reload', 'error')
  }
}

// Watch for account changes to reset envelope selection
watch(formAccountId, (newId, oldId) => {
  if (!newId || !oldId) return

  const oldAccount = accountsStore.accounts.find((a) => a.id === oldId)
  const newAccount = accountsStore.accounts.find((a) => a.id === newId)

  // Reset envelope selection when switching between budget/non-budget accounts
  if (oldAccount?.include_in_budget !== newAccount?.include_in_budget) {
    formEnvelopeId.value = null
  }
})

// Watch for transfer account changes to reset envelope when no longer budget->tracking
watch([formAccountId, formDestinationAccountId, formIsTransfer], () => {
  if (formIsTransfer.value && !isBudgetToTrackingTransfer.value) {
    formEnvelopeId.value = null
  }
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">
        Recurring Transactions
      </h1>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Add Recurring
      </v-btn>
    </div>

    <!-- Summary Cards -->
    <v-row class="mb-4">
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text class="text-center">
            <div class="text-subtitle-2 text-medium-emphasis">
              Monthly Expenses
            </div>
            <MoneyDisplay
              :amount="-recurringStore.totalMonthlyExpenses"
              class="text-h6 text-error"
            />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text class="text-center">
            <div class="text-subtitle-2 text-medium-emphasis">
              Monthly Income
            </div>
            <MoneyDisplay
              :amount="recurringStore.totalMonthlyIncome"
              class="text-h6 text-success"
            />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text class="text-center">
            <div class="text-subtitle-2 text-medium-emphasis">
              Net Monthly
            </div>
            <MoneyDisplay
              :amount="recurringStore.totalMonthlyIncome - recurringStore.totalMonthlyExpenses"
              class="text-h6"
            />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text class="text-center">
            <div class="text-subtitle-2 text-medium-emphasis">
              Active Rules
            </div>
            <div class="text-h6">
              {{ recurringStore.activeRecurring.length }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-switch
          v-model="showInactive"
          label="Show inactive"
          hide-details
          density="compact"
          @update:model-value="handleShowInactiveChange"
        />
      </v-card-text>
    </v-card>

    <!-- Loading State -->
    <div
      v-if="recurringStore.loading && recurringStore.recurringTransactions.length === 0"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <!-- Empty State -->
    <v-card v-else-if="sortedRecurring.length === 0">
      <v-card-text class="text-center text-grey py-8">
        <v-icon
          size="64"
          color="grey-lighten-1"
        >
          mdi-repeat
        </v-icon>
        <p class="mt-4">
          No recurring transactions yet.
        </p>
        <p class="text-body-2">
          Set up recurring transactions for regular bills, subscriptions, and income!
        </p>
        <v-btn
          color="primary"
          class="mt-4"
          @click="openCreateDialog"
        >
          Add Recurring Transaction
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- Recurring List -->
    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="recurring in sortedRecurring"
          :key="recurring.id"
          :class="{ 'opacity-50': !recurring.is_active }"
        >
          <template #prepend>
            <v-avatar
              :color="getIconColor(recurring)"
              variant="tonal"
              size="40"
            >
              <v-icon>{{ getIcon(recurring) }}</v-icon>
            </v-avatar>
          </template>

          <v-list-item-title class="font-weight-medium">
            {{ getDisplayName(recurring) }}
            <v-chip
              v-if="!recurring.is_active"
              size="x-small"
              color="grey"
              class="ml-2"
            >
              Paused
            </v-chip>
          </v-list-item-title>

          <v-list-item-subtitle>
            <span>{{ getAccountName(recurring.account_id) }}</span>
            <span class="mx-1">·</span>
            <span>{{ formatFrequency(recurring) }}</span>
            <span class="mx-1">·</span>
            <span>Next: {{ formatNextDate(recurring.next_scheduled_date || recurring.next_occurrence_date) }}</span>
            <template v-if="getEnvelopeName(recurring.envelope_id)">
              <span class="mx-1">·</span>
              <span>{{ getEnvelopeName(recurring.envelope_id) }}</span>
            </template>
          </v-list-item-subtitle>

          <template #append>
            <MoneyDisplay
              :amount="recurring.amount"
              class="font-weight-medium mr-2"
            />
            <v-menu>
              <template #activator="{ props }">
                <v-btn
                  icon="mdi-dots-vertical"
                  size="small"
                  variant="text"
                  v-bind="props"
                />
              </template>
              <v-list density="compact">
                <v-list-item @click="openEditDialog(recurring)">
                  <v-list-item-title>Edit</v-list-item-title>
                </v-list-item>
                <v-list-item @click="toggleActive(recurring)">
                  <v-list-item-title>
                    {{ recurring.is_active ? 'Pause' : 'Resume' }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item
                  class="text-error"
                  @click="openDeleteDialog(recurring)"
                >
                  <v-list-item-title>Delete</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Form Dialog -->
    <v-dialog
      v-model="showFormDialog"
      max-width="500"
    >
      <v-card>
        <v-card-title>
          {{ editingId ? 'Edit Recurring Transaction' : 'New Recurring Transaction' }}
        </v-card-title>
        <v-card-text>
          <!-- Transaction Type -->
          <v-btn-toggle
            v-model="formIsTransfer"
            mandatory
            density="compact"
            class="mb-4"
          >
            <v-btn :value="false">
              Transaction
            </v-btn>
            <v-btn :value="true">
              Transfer
            </v-btn>
          </v-btn-toggle>

          <!-- Account -->
          <AccountSelect
            v-model="formAccountId"
            :label="formIsTransfer ? 'From Account' : 'Account'"
            class="mb-4"
          />

          <!-- For transfers: destination account -->
          <AccountSelect
            v-if="formIsTransfer"
            v-model="formDestinationAccountId"
            label="To Account"
            :exclude-ids="formAccountId ? [formAccountId] : []"
            class="mb-4"
          />

          <!-- Envelope (for budget -> tracking transfers) -->
          <EnvelopeSelect
            v-if="isBudgetToTrackingTransfer"
            v-model="formEnvelopeId"
            label="Envelope"
            :rules="required"
            :include-unallocated="false"
            hint="Which envelope is this money coming from?"
            persistent-hint
            class="mb-4"
          />

          <!-- For regular: payee -->
          <PayeeSelect
            v-if="!formIsTransfer"
            v-model="formPayeeId"
            class="mb-4"
          />

          <!-- Amount -->
          <div
            v-if="!formIsTransfer"
            class="d-flex gap-2 mb-4"
          >
            <v-btn-toggle
              v-model="formIsExpense"
              mandatory
              density="compact"
            >
              <v-btn :value="true">
                Expense
              </v-btn>
              <v-btn :value="false">
                Income
              </v-btn>
            </v-btn-toggle>
          </div>

          <MoneyInput
            v-model="formAmount"
            class="mb-4"
          />

          <!-- Frequency -->
          <v-row class="mb-4">
            <v-col cols="4">
              <v-text-field
                v-model="formFrequencyValue"
                label="Every"
                type="number"
                min="1"
                hide-details
              />
            </v-col>
            <v-col cols="8">
              <v-select
                v-model="formFrequencyUnit"
                label="Period"
                :items="frequencyUnitOptions"
                hide-details
              />
            </v-col>
          </v-row>

          <!-- Dates -->
          <v-text-field
            v-model="formStartDate"
            label="Start Date"
            type="date"
            class="mb-4"
          />

          <v-text-field
            v-model="formEndDate"
            label="End Date (optional)"
            type="date"
            clearable
            class="mb-4"
          />

          <!-- Envelope (for budget account expenses - required) -->
          <EnvelopeSelect
            v-if="isInBudgetAccount && !formIsTransfer && formIsExpense"
            v-model="formEnvelopeId"
            label="Envelope"
            :clearable="false"
            :rules="required"
            :include-unallocated="false"
            hint="Required for expenses"
            persistent-hint
            class="mb-4"
          />

          <!-- Envelope (for budget account income - optional) -->
          <EnvelopeSelect
            v-if="isInBudgetAccount && !formIsTransfer && !formIsExpense"
            v-model="formEnvelopeId"
            label="Envelope"
            clearable
            include-unallocated
            hint="Leave empty to use Unallocated"
            persistent-hint
            class="mb-4"
          />

          <!-- Memo -->
          <v-text-field
            v-model="formMemo"
            label="Memo (optional)"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showFormDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="formLoading"
            :disabled="!formAccountId || !formAmount || (formIsTransfer && !formDestinationAccountId) || (!formIsTransfer && !formPayeeId) || (isEnvelopeRequired && !formEnvelopeId) || (isBudgetToTrackingTransfer && !formEnvelopeId)"
            @click="handleSubmit"
          >
            {{ editingId ? 'Save' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Delete Recurring Transaction</v-card-title>
        <v-card-text>
          <p class="mb-4">
            Are you sure you want to delete this recurring transaction?
          </p>

          <v-checkbox
            v-model="deleteScheduled"
            label="Also delete future scheduled occurrences"
            hint="Uncheck to keep existing scheduled transactions"
            persistent-hint
            hide-details
          />
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
            :loading="deleting"
            @click="handleDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
