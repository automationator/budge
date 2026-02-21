<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import { usePayeesStore } from '@/stores/payees'
import { useEnvelopesStore } from '@/stores/envelopes'
import { useLocationsStore } from '@/stores/locations'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import { useAuthStore } from '@/stores/auth'
import type { RulePreviewAllocation } from '@/api/allocationRules'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import AccountSelect from '@/components/common/AccountSelect.vue'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import PayeeSelect from '@/components/common/PayeeSelect.vue'
import LocationSelect from '@/components/common/LocationSelect.vue'
import type { AllocationInput } from '@/api/transactions'
import type { Transaction } from '@/types'
import { toLocaleDateString } from '@/utils/date'

const props = defineProps<{
  modelValue: boolean
  accountId?: string | null
  envelopeId?: string | null
  transactionId?: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [transaction: Transaction]
  updated: [transaction: Transaction]
  deleted: [transactionId: string]
}>()

const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const payeesStore = usePayeesStore()
const envelopesStore = useEnvelopesStore()
const locationsStore = useLocationsStore()
const allocationRulesStore = useAllocationRulesStore()
const authStore = useAuthStore()
const { mobile } = useDisplay()

const fieldDensity = computed(() => mobile.value ? 'compact' as const : 'default' as const)
const fieldSpacing = computed(() => mobile.value ? 'mt-1' : 'mt-2')
const fieldHideDetails = computed(() => mobile.value ? 'auto' as const : false as const)

const isEditing = computed(() => !!props.transactionId)

// Form state
const loading = ref(false)
const formValid = ref(false)
const transactionType = ref<'standard' | 'transfer' | 'adjustment'>('standard')

// Standard transaction fields
const formAccountId = ref<string | null>(null)
const payeeId = ref<string | null>(null)
const amount = ref<string>('')
const isExpense = ref(true)
const date = ref(toLocaleDateString())
const isCleared = ref(false)
const memo = ref('')
const locationId = ref<string | null>(null)

// Transfer fields
const sourceAccountId = ref<string | null>(null)
const destinationAccountId = ref<string | null>(null)
const transferEnvelopeId = ref<string | null>(null)
const editingSourceSide = ref(true)

// Envelope selection (for budget accounts)
const selectedEnvelopeId = ref<string | null>(null)
const isSplitMode = ref(false)
const allocations = ref<{ envelope_id: string; amount: string; memo: string }[]>([])

// Income allocation mode ('rules', 'envelope', 'unallocated')
const incomeAllocationMode = ref<'rules' | 'envelope' | 'unallocated'>('rules')

// Preview dialog state
const showPreviewDialog = ref(false)
const previewAllocations = ref<RulePreviewAllocation[]>([])
const previewUnallocated = ref(0)
const previewLoading = ref(false)

// Delete confirmation
const showDeleteDialog = ref(false)
const deleting = ref(false)

// Validation rules
const required = [(v: unknown) => !!v || 'Required']

// Computed
const dialogOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})


const isInBudgetAccount = computed(() => {
  if (!formAccountId.value) return false
  const account = accountsStore.accounts.find((a) => a.id === formAccountId.value)
  return account?.include_in_budget ?? false
})

// Check if transfer is from budget account to tracking account (money leaving budget)
const isBudgetToTrackingTransfer = computed(() => {
  if (transactionType.value !== 'transfer') return false
  if (!sourceAccountId.value || !destinationAccountId.value) return false

  const source = accountsStore.accounts.find((a) => a.id === sourceAccountId.value)
  const dest = accountsStore.accounts.find((a) => a.id === destinationAccountId.value)

  return source?.include_in_budget === true && dest?.include_in_budget === false
})

const envelopeLabel = computed(() => 'Envelope')

// Envelope is required for expenses in budget accounts (not for income)
const isEnvelopeRequired = computed(() => {
  return isInBudgetAccount.value && isExpense.value && transactionType.value === 'standard'
})

// Check if split mode has valid allocations (at least one with envelope selected)
const isSplitModeValid = computed(() => {
  if (!isSplitMode.value) return true
  if (!isEnvelopeRequired.value) return true
  return allocations.value.some((a) => a.envelope_id && parseFloat(a.amount) > 0)
})

// Check if there are active allocation rules
const hasActiveRules = computed(() => allocationRulesStore.activeRules.length > 0)

// Show income allocation options when creating income in a budget account (not split mode)
const showIncomeAllocationOptions = computed(() =>
  !isExpense.value &&
  isInBudgetAccount.value &&
  !isSplitMode.value &&
  transactionType.value === 'standard' &&
  !isEditing.value
)

const amountInCents = computed(() => {
  const parsed = parseFloat(amount.value) || 0
  const cents = Math.round(parsed * 100)
  return transactionType.value === 'transfer' ? cents : isExpense.value ? -cents : cents
})

const allocatedAmount = computed(() => {
  return allocations.value.reduce((sum, a) => {
    const parsed = parseFloat(a.amount) || 0
    return sum + Math.round(parsed * 100)
  }, 0)
})

const unallocatedAmount = computed(() => {
  return Math.abs(amountInCents.value) - allocatedAmount.value
})

const isTransfer = computed(() => {
  if (isEditing.value && props.transactionId) {
    const txn = transactionsStore.getTransactionById(props.transactionId)
    return txn?.transaction_type === 'transfer'
  }
  return transactionType.value === 'transfer'
})

const isAdjustment = computed(() => {
  if (isEditing.value && props.transactionId) {
    const txn = transactionsStore.getTransactionById(props.transactionId)
    return txn?.transaction_type === 'adjustment'
  }
  return transactionType.value === 'adjustment'
})

const dialogTitle = computed(() => {
  if (isEditing.value) {
    if (isTransfer.value) return 'Edit Transfer'
    if (isAdjustment.value) return 'Edit Adjustment'
    return 'Edit Transaction'
  }
  return transactionType.value === 'transfer' ? 'New Transfer' : 'New Transaction'
})

// Load data when dialog opens
watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      await loadFormData()
    }
  },
  { immediate: true }
)

async function loadFormData() {
  try {
    await Promise.all([
      accountsStore.fetchAccounts(),
      payeesStore.fetchPayees(),
      locationsStore.fetchLocations(),
      envelopesStore.fetchEnvelopeGroups(),
      envelopesStore.fetchEnvelopes(),
      allocationRulesStore.fetchAllocationRules(),
    ])

    if (isEditing.value && props.transactionId) {
      await loadTransaction()
    } else {
      resetForm()
      // Apply accountId prop if provided
      if (props.accountId) {
        formAccountId.value = props.accountId
      }
    }
  } catch {
    showSnackbar('Failed to load form data', 'error')
  }
}

async function loadTransaction() {
  if (!props.transactionId) return

  try {
    loading.value = true
    const transaction = await transactionsStore.fetchTransaction(props.transactionId)

    if (transaction.transaction_type === 'transfer') {
      transactionType.value = 'transfer'
      // For transfers, this transaction could be source or destination
      // Amount > 0 means this is the destination (money coming in)
      if (transaction.amount > 0) {
        destinationAccountId.value = transaction.account_id
        sourceAccountId.value = transaction.linked_account_id
        editingSourceSide.value = false
      } else {
        sourceAccountId.value = transaction.account_id
        destinationAccountId.value = transaction.linked_account_id
        editingSourceSide.value = true
      }
      amount.value = (Math.abs(transaction.amount) / 100).toFixed(2)
      // Load envelope from allocations for budget-to-tracking transfers
      if (transaction.allocations && transaction.allocations.length > 0) {
        transferEnvelopeId.value = transaction.allocations[0]!.envelope_id
      }
    } else if (transaction.transaction_type === 'adjustment') {
      transactionType.value = 'adjustment'
      formAccountId.value = transaction.account_id
      payeeId.value = null // Adjustments don't have payees
      isExpense.value = transaction.amount < 0
      amount.value = (Math.abs(transaction.amount) / 100).toFixed(2)
    } else {
      transactionType.value = 'standard'
      formAccountId.value = transaction.account_id
      payeeId.value = transaction.payee_id
      isExpense.value = transaction.amount < 0
      amount.value = (Math.abs(transaction.amount) / 100).toFixed(2)
    }

    date.value = transaction.date
    isCleared.value = transaction.is_cleared
    memo.value = transaction.memo || ''
    locationId.value = transaction.location_id || null

    // Load existing allocations (for standard transactions)
    if (
      transaction.transaction_type === 'standard' &&
      transaction.allocations &&
      transaction.allocations.length > 0
    ) {
      // For credit card accounts, filter out the auto-generated CC envelope allocation
      // The CC envelope has linked_account_id matching the transaction's account
      const ccEnvelope = envelopesStore.envelopes.find(
        (e) => e.linked_account_id === transaction.account_id
      )
      const userAllocations = ccEnvelope
        ? transaction.allocations.filter((a) => a.envelope_id !== ccEnvelope.id)
        : transaction.allocations

      if (userAllocations.length === 1) {
        // Single allocation - use single envelope mode
        selectedEnvelopeId.value = userAllocations[0]!.envelope_id
        isSplitMode.value = false
      } else if (userAllocations.length > 1) {
        // Multiple allocations - use split mode
        isSplitMode.value = true
        allocations.value = userAllocations.map((a) => ({
          envelope_id: a.envelope_id,
          amount: (Math.abs(a.amount) / 100).toFixed(2),
          memo: a.memo || '',
        }))
      }
      // If userAllocations.length === 0, leave envelope unselected
    }
  } catch {
    showSnackbar('Failed to load transaction', 'error')
    closeDialog()
  } finally {
    loading.value = false
  }
}

function resetForm() {
  transactionType.value = 'standard'
  formAccountId.value = null
  payeeId.value = null
  amount.value = ''
  isExpense.value = true
  date.value = toLocaleDateString()
  isCleared.value = false
  memo.value = ''
  locationId.value = null
  sourceAccountId.value = null
  destinationAccountId.value = null
  transferEnvelopeId.value = null
  editingSourceSide.value = true
  selectedEnvelopeId.value = null
  isSplitMode.value = false
  allocations.value = []
  // Set income allocation mode from budget default
  const currentBudget = authStore.budgets.find((b) => b.id === authStore.currentBudgetId)
  incomeAllocationMode.value = currentBudget?.default_income_allocation ?? 'rules'
  // Reset preview state
  showPreviewDialog.value = false
  previewAllocations.value = []
  previewUnallocated.value = 0
}

function closeDialog() {
  dialogOpen.value = false
}

// Watch for account changes to reset envelope selection
watch(formAccountId, (newId, oldId) => {
  if (!newId || !oldId) return

  const oldAccount = accountsStore.accounts.find((a) => a.id === oldId)
  const newAccount = accountsStore.accounts.find((a) => a.id === newId)

  // Reset envelope selection when switching between budget/non-budget accounts
  if (oldAccount?.include_in_budget !== newAccount?.include_in_budget) {
    selectedEnvelopeId.value = null
    isSplitMode.value = false
    allocations.value = []
  }
})

// Watch for in-budget account selection to auto-fill preselected envelope
watch(isInBudgetAccount, (inBudget) => {
  // When switching to an in-budget account, auto-select the preselected envelope
  // (only if envelope not already selected, not editing, and not in split mode)
  if (
    inBudget &&
    props.envelopeId &&
    !selectedEnvelopeId.value &&
    !isEditing.value &&
    !isSplitMode.value
  ) {
    selectedEnvelopeId.value = props.envelopeId
  }
})

// Watch for payee changes to auto-fill envelope
watch(payeeId, (newPayeeId, oldPayeeId) => {
  // Only auto-fill if:
  // 1. A new payee was selected (not cleared)
  // 2. We're in a budget account
  // 3. Envelope is not already selected (don't override user's choice)
  // 4. Not editing (only for new transactions)
  // 5. Not in split mode
  if (
    newPayeeId &&
    newPayeeId !== oldPayeeId &&
    isInBudgetAccount.value &&
    !selectedEnvelopeId.value &&
    !isEditing.value &&
    !isSplitMode.value
  ) {
    const defaultEnvelope = payeesStore.getDefaultEnvelopeId(newPayeeId)
    if (defaultEnvelope) {
      selectedEnvelopeId.value = defaultEnvelope
    }
  }
})

// Watch for transfer account changes to reset envelope when no longer budget->tracking
watch([sourceAccountId, destinationAccountId], () => {
  if (!isBudgetToTrackingTransfer.value) {
    transferEnvelopeId.value = null
  }
})

function enableSplitMode() {
  isSplitMode.value = true
  // If single envelope was selected, start with that as first allocation
  if (selectedEnvelopeId.value && amount.value) {
    allocations.value = [
      {
        envelope_id: selectedEnvelopeId.value,
        amount: amount.value,
        memo: '',
      },
    ]
  } else {
    allocations.value = []
  }
  selectedEnvelopeId.value = null
}

function disableSplitMode() {
  isSplitMode.value = false
  // If only one allocation, use it as single envelope
  if (allocations.value.length === 1 && allocations.value[0]!.envelope_id) {
    selectedEnvelopeId.value = allocations.value[0]!.envelope_id
  } else {
    selectedEnvelopeId.value = null
  }
  allocations.value = []
}

function addAllocation() {
  allocations.value.push({ envelope_id: '', amount: '', memo: '' })
}

function removeAllocation(index: number) {
  allocations.value.splice(index, 1)
}

function autoFillRemainder(index: number) {
  const remaining = unallocatedAmount.value / 100
  if (remaining > 0) {
    allocations.value[index]!.amount = remaining.toFixed(2)
  }
}

async function handleSubmit(addAnother = false) {
  if (!formValid.value) return

  // For new income transactions with "rules" mode, show preview first
  if (
    !isEditing.value &&
    !isExpense.value &&
    isInBudgetAccount.value &&
    incomeAllocationMode.value === 'rules' &&
    transactionType.value === 'standard'
  ) {
    await showAllocationPreview()
    return
  }

  await submitTransaction(addAnother)
}

async function showAllocationPreview() {
  previewLoading.value = true
  try {
    const response = await allocationRulesStore.previewRules(amountInCents.value)
    previewAllocations.value = response.allocations
    previewUnallocated.value = response.unallocated
    showPreviewDialog.value = true
  } catch {
    showSnackbar('Failed to preview allocation rules', 'error')
  } finally {
    previewLoading.value = false
  }
}

async function confirmPreviewAndSubmit() {
  showPreviewDialog.value = false
  await submitTransaction(false)
}

async function submitTransaction(addAnother = false) {
  loading.value = true

  try {
    let result: Transaction

    if (transactionType.value === 'transfer') {
      result = await handleTransferSubmit()
    } else {
      result = await handleStandardSubmit()
    }

    if (isEditing.value) {
      emit('updated', result)
      closeDialog()
    } else {
      emit('created', result)
      if (addAnother) {
        // Reset form but keep accountId if provided via prop
        resetForm()
        if (props.accountId) {
          formAccountId.value = props.accountId
        }
      } else {
        closeDialog()
      }
    }
  } catch {
    showSnackbar(
      isEditing.value ? 'Failed to update transaction' : 'Failed to create transaction',
      'error'
    )
  } finally {
    loading.value = false
  }
}

async function handleStandardSubmit(): Promise<Transaction> {
  // Build allocations from either single envelope or split mode
  let allocationInputs: AllocationInput[] = []

  if (isInBudgetAccount.value) {
    if (isSplitMode.value) {
      // Use split allocations (amounts need to match transaction sign)
      allocationInputs = allocations.value
        .filter((a) => a.envelope_id && parseFloat(a.amount) > 0)
        .map((a) => ({
          envelope_id: a.envelope_id,
          amount: isExpense.value
            ? -Math.round(parseFloat(a.amount) * 100)
            : Math.round(parseFloat(a.amount) * 100),
          memo: a.memo.trim() || null,
        }))
    } else if (selectedEnvelopeId.value) {
      // Single envelope selection
      allocationInputs = [
        {
          envelope_id: selectedEnvelopeId.value,
          amount: amountInCents.value,
          memo: null,
        },
      ]
    }
    // If no envelope selected, backend will default to Unallocated
  }

  if (isEditing.value && props.transactionId) {
    // For adjustments, don't send payee_id
    return await transactionsStore.updateTransaction(props.transactionId, {
      account_id: formAccountId.value!,
      payee_id: isAdjustment.value ? null : payeeId.value,
      date: date.value,
      amount: amountInCents.value,
      is_cleared: isCleared.value,
      memo: memo.value.trim() || null,
      location_id: locationId.value,
      allocations: isInBudgetAccount.value ? allocationInputs : undefined,
    })
  } else {
    // For income with "rules" mode, use apply_allocation_rules
    const useAutoDistribute =
      !isExpense.value &&
      isInBudgetAccount.value &&
      incomeAllocationMode.value === 'rules' &&
      !isSplitMode.value

    return await transactionsStore.createTransaction({
      account_id: formAccountId.value!,
      payee_id: payeeId.value!,
      date: date.value,
      amount: amountInCents.value,
      is_cleared: isCleared.value,
      memo: memo.value.trim() || null,
      location_id: locationId.value,
      allocations: useAutoDistribute ? undefined : allocationInputs.length > 0 ? allocationInputs : undefined,
      apply_allocation_rules: useAutoDistribute,
    })
  }
}

async function handleTransferSubmit(): Promise<Transaction> {
  const transferAmount = Math.round((parseFloat(amount.value) || 0) * 100)

  if (isEditing.value && props.transactionId) {
    const result = await transactionsStore.updateTransfer(props.transactionId, {
      source_account_id: sourceAccountId.value!,
      destination_account_id: destinationAccountId.value!,
      amount: transferAmount,
      date: date.value,
      memo: memo.value.trim() || null,
      envelope_id: isBudgetToTrackingTransfer.value ? transferEnvelopeId.value : undefined,
      ...(editingSourceSide.value
        ? { source_is_cleared: isCleared.value }
        : { destination_is_cleared: isCleared.value }),
    })
    return result.source_transaction
  } else {
    const result = await transactionsStore.createTransfer({
      source_account_id: sourceAccountId.value!,
      destination_account_id: destinationAccountId.value!,
      amount: transferAmount,
      date: date.value,
      is_cleared: isCleared.value,
      memo: memo.value.trim() || null,
      envelope_id: isBudgetToTrackingTransfer.value ? transferEnvelopeId.value : undefined,
    })
    return result.source_transaction
  }
}

async function handleDelete() {
  if (!props.transactionId) return

  try {
    deleting.value = true

    if (isTransfer.value) {
      await transactionsStore.deleteTransfer(props.transactionId)
    } else {
      await transactionsStore.deleteTransaction(props.transactionId)
    }

    emit('deleted', props.transactionId)
    closeDialog()
  } catch {
    showSnackbar('Failed to delete transaction', 'error')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}
</script>

<template>
  <v-dialog
    v-model="dialogOpen"
    :fullscreen="mobile"
    :max-width="mobile ? undefined : 600"
  >
    <v-card :class="{ 'd-flex flex-column': mobile }">
      <v-card-title class="d-flex align-center">
        <span>{{ dialogTitle }}</span>
        <v-spacer />
        <v-btn
          :icon="isCleared ? 'mdi-check-circle' : 'mdi-check-circle-outline'"
          :color="isCleared ? 'success' : undefined"
          variant="text"
          size="small"
          :title="isCleared ? 'Cleared' : 'Uncleared'"
          data-testid="cleared-toggle"
          @click="isCleared = !isCleared"
        />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          @click="closeDialog"
        />
      </v-card-title>

      <!-- Transaction Type Tabs (only for new transactions) -->
      <v-tabs
        v-if="!isEditing"
        v-model="transactionType"
        class="px-4"
      >
        <v-tab value="standard">
          Transaction
        </v-tab>
        <v-tab value="transfer">
          Transfer
        </v-tab>
      </v-tabs>

      <v-card-text :class="{ 'mobile-form-scroll': mobile }">
        <v-form
          v-model="formValid"
          @submit.prevent="handleSubmit(false)"
        >
          <!-- Standard Transaction Form -->
          <template v-if="transactionType === 'standard' || transactionType === 'adjustment'">
            <!-- Adjustment notice -->
            <v-alert
              v-if="isAdjustment"
              type="info"
              variant="tonal"
              class="mb-4"
            >
              This is a balance adjustment transaction. Adjustments don't have a payee.
            </v-alert>

            <!-- Account -->
            <AccountSelect
              v-model="formAccountId"
              label="Account"
              :rules="required"
              :disabled="loading"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />

            <!-- Payee (only for non-adjustment transactions) -->
            <PayeeSelect
              v-if="!isAdjustment"
              v-model="payeeId"
              :rules="required"
              :disabled="loading"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
              clearable
            />

            <!-- Envelope Selection (for budget accounts) -->
            <template v-if="isInBudgetAccount && !isAdjustment">
              <div :class="['d-flex align-center justify-space-between', fieldSpacing, mobile ? 'mb-1' : 'mb-2']">
                <span class="text-subtitle-1 font-weight-medium">{{ envelopeLabel }}</span>
                <v-btn
                  v-if="!isSplitMode && !showIncomeAllocationOptions"
                  variant="text"
                  size="small"
                  @click="enableSplitMode"
                >
                  Split across envelopes
                </v-btn>
                <v-btn
                  v-else-if="isSplitMode"
                  variant="text"
                  size="small"
                  @click="disableSplitMode"
                >
                  Use single {{ envelopeLabel.toLowerCase() }}
                </v-btn>
              </div>

              <!-- Income Allocation Mode Selector (for new income transactions) -->
              <template v-if="showIncomeAllocationOptions">
                <v-radio-group
                  v-model="incomeAllocationMode"
                  inline
                  density="compact"
                  hide-details
                  class="mb-2"
                >
                  <v-radio
                    v-if="hasActiveRules"
                    label="Auto-distribute"
                    value="rules"
                  />
                  <v-radio
                    label="Envelope"
                    value="envelope"
                  />
                  <v-radio
                    label="None"
                    value="unallocated"
                  />
                </v-radio-group>

                <!-- Envelope dropdown for "envelope" mode -->
                <EnvelopeSelect
                  v-if="incomeAllocationMode === 'envelope'"
                  v-model="selectedEnvelopeId"
                  :label="envelopeLabel"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                  clearable
                  include-unallocated
                />
              </template>

              <!-- Single Envelope Mode (for expenses or editing) -->
              <template v-else-if="!isSplitMode">
                <EnvelopeSelect
                  v-model="selectedEnvelopeId"
                  :label="envelopeLabel"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                  :clearable="!isEnvelopeRequired"
                  :rules="isEnvelopeRequired ? required : []"
                  :include-unallocated="!isEnvelopeRequired"
                  :hint="isEnvelopeRequired ? 'Required for expenses' : 'Leave empty to use Unallocated'"
                  persistent-hint
                />
              </template>

              <!-- Split Mode -->
              <template v-else>
                <div
                  v-for="(allocation, index) in allocations"
                  :key="index"
                  class="d-flex gap-2 mb-2 align-center"
                >
                  <EnvelopeSelect
                    v-model="allocation.envelope_id"
                    :label="envelopeLabel"
                    :include-unallocated="!isEnvelopeRequired"
                    density="compact"
                    hide-details
                    style="flex: 2"
                  />
                  <v-text-field
                    v-model="allocation.amount"
                    label="Amount"
                    type="number"
                    step="0.01"
                    min="0"
                    prefix="$"
                    density="compact"
                    hide-details
                    style="flex: 1"
                    @focus="autoFillRemainder(index)"
                  />
                  <v-btn
                    icon="mdi-close"
                    size="small"
                    variant="text"
                    @click="removeAllocation(index)"
                  />
                </div>

                <v-btn
                  variant="tonal"
                  size="small"
                  prepend-icon="mdi-plus"
                  class="mt-2"
                  @click="addAllocation"
                >
                  Add Allocation
                </v-btn>

                <div
                  v-if="allocations.length > 0"
                  class="mt-4 text-body-2"
                >
                  <div class="d-flex justify-space-between">
                    <span>Total Amount:</span>
                    <MoneyDisplay :amount="Math.abs(amountInCents)" />
                  </div>
                  <div class="d-flex justify-space-between">
                    <span>Allocated:</span>
                    <MoneyDisplay :amount="allocatedAmount" />
                  </div>
                  <div class="d-flex justify-space-between font-weight-medium">
                    <span>Unallocated:</span>
                    <MoneyDisplay :amount="unallocatedAmount" />
                  </div>
                </div>

                <!-- Split mode validation error -->
                <v-alert
                  v-if="isEnvelopeRequired && !isSplitModeValid"
                  type="error"
                  variant="tonal"
                  density="compact"
                  class="mt-2"
                >
                  At least one envelope allocation is required for expenses
                </v-alert>
              </template>
            </template>

            <!-- Date and Amount -->
            <v-row :class="fieldSpacing" dense>
              <v-col :cols="mobile ? 6 : 12">
                <v-text-field
                  v-model="date"
                  label="Date"
                  type="date"
                  :rules="required"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                />
              </v-col>
              <v-col :cols="mobile ? 6 : 12" :class="mobile ? '' : fieldSpacing">
                <MoneyInput
                  v-model="amount"
                  v-model:is-expense="isExpense"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                />
              </v-col>
            </v-row>

            <!-- Memo -->
            <v-text-field
              v-model="memo"
              label="Memo (optional)"
              :disabled="loading"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />

            <!-- Location -->
            <LocationSelect
              v-model="locationId"
              label="Location (optional)"
              clearable
              :disabled="loading"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />
          </template>

          <!-- Transfer Form -->
          <template v-else>
            <AccountSelect
              v-model="sourceAccountId"
              label="From Account"
              :rules="required"
              :disabled="loading"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />

            <AccountSelect
              v-model="destinationAccountId"
              label="To Account"
              :exclude-ids="sourceAccountId ? [sourceAccountId] : []"
              :rules="required"
              :disabled="loading || !sourceAccountId"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />

            <!-- Envelope (for budget -> tracking transfers) -->
            <EnvelopeSelect
              v-if="isBudgetToTrackingTransfer"
              v-model="transferEnvelopeId"
              label="Envelope"
              :rules="required"
              :disabled="loading"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
              hint="Which envelope is this money coming from?"
              persistent-hint
            />

            <!-- Date and Amount -->
            <v-row :class="fieldSpacing" dense>
              <v-col :cols="mobile ? 6 : 12">
                <v-text-field
                  v-model="date"
                  label="Date"
                  type="date"
                  :rules="required"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                />
              </v-col>
              <v-col :cols="mobile ? 6 : 12" :class="mobile ? '' : fieldSpacing">
                <MoneyInput
                  v-model="amount"
                  :disabled="loading"
                  :density="fieldDensity"
                  :hide-details="fieldHideDetails"
                />
              </v-col>
            </v-row>

            <!-- Memo -->
            <v-text-field
              v-model="memo"
              label="Memo (optional)"
              :disabled="loading"
              :class="fieldSpacing"
              :density="fieldDensity"
              :hide-details="fieldHideDetails"
            />
          </template>
        </v-form>
      </v-card-text>

      <v-card-actions :class="['justify-end', { 'mobile-sticky-actions': mobile }]">
        <v-btn
          v-if="isEditing"
          color="error"
          variant="text"
          class="mr-auto"
          @click="showDeleteDialog = true"
        >
          Delete
        </v-btn>
        <v-btn
          variant="text"
          :disabled="loading"
          @click="closeDialog"
        >
          Cancel
        </v-btn>
        <v-btn
          v-if="!isEditing"
          variant="tonal"
          color="primary"
          :loading="loading"
          :disabled="!formValid || !isSplitModeValid"
          @click="handleSubmit(true)"
        >
          Save & Add Another
        </v-btn>
        <v-btn
          variant="elevated"
          color="primary"
          :loading="loading"
          :disabled="!formValid || !isSplitModeValid"
          @click="handleSubmit(false)"
        >
          {{ isEditing ? 'Save' : 'Create' }}
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Delete Transaction</v-card-title>
        <v-card-text>
          Are you sure you want to delete this transaction? This action cannot be undone.
          <template v-if="isTransfer">
            <br><br>
            <strong>Note:</strong> This will delete both sides of the transfer.
          </template>
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

    <!-- Allocation Preview Dialog -->
    <v-dialog
      v-model="showPreviewDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Allocation Preview</v-card-title>
        <v-card-text>
          <div
            v-for="allocation in previewAllocations"
            :key="allocation.envelope_id"
            class="d-flex justify-space-between mb-2"
          >
            <span>{{ envelopesStore.getEnvelopeById(allocation.envelope_id)?.name || 'Unknown' }}</span>
            <MoneyDisplay :amount="allocation.amount" />
          </div>
          <div
            v-if="previewUnallocated > 0"
            class="d-flex justify-space-between mb-2 text-medium-emphasis"
          >
            <span>Unallocated (remainder)</span>
            <MoneyDisplay :amount="previewUnallocated" />
          </div>
          <v-divider class="my-2" />
          <div class="d-flex justify-space-between font-weight-bold">
            <span>Total</span>
            <MoneyDisplay :amount="amountInCents" />
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showPreviewDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="loading"
            @click="confirmPreviewAndSubmit"
          >
            Confirm & Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<style>
/* Mobile transaction form compact layout */
.mobile-form-scroll {
  overflow-y: auto;
  flex: 1 1 0;
  min-height: 0;
  padding-top: 8px;
  padding-bottom: 8px;
}

.mobile-sticky-actions {
  position: sticky;
  bottom: 0;
  z-index: 1;
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* Improve disabled button visibility in dark mode */
/* Dialog renders in overlay container - target via theme class on overlay */

/* Elevated (default) variant - primary color button when disabled */
.v-theme--dark .v-btn--variant-elevated.v-btn--disabled.bg-primary {
  background-color: rgb(var(--v-theme-primary)) !important;
  opacity: 0.5 !important;
}

.v-theme--dark .v-btn--variant-elevated.v-btn--disabled.bg-primary .v-btn__content {
  color: white !important;
  opacity: 1 !important;
}

/* Tonal variant - lighter background with colored text */
.v-theme--dark .v-btn--variant-tonal.v-btn--disabled {
  background-color: rgba(var(--v-theme-primary), 0.25) !important;
  opacity: 1 !important;
}

.v-theme--dark .v-btn--variant-tonal.v-btn--disabled .v-btn__content {
  color: rgb(var(--v-theme-primary)) !important;
  opacity: 0.8 !important;
}
</style>
