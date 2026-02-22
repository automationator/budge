<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useEnvelopesStore, type DateRangePreset } from '@/stores/envelopes'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import EnvelopeBudgetRow from '@/components/envelopes/EnvelopeBudgetRow.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import AllocationRuleForm from '@/components/allocation-rules/AllocationRuleForm.vue'
import OverspentAlert from '@/components/envelopes/OverspentAlert.vue'
import BalanceRepairAlert from '@/components/envelopes/BalanceRepairAlert.vue'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import DateRangePicker from '@/components/common/DateRangePicker.vue'
import EnvelopeActivityDialog from '@/components/envelopes/EnvelopeActivityDialog.vue'
import BudgetSummaryPanel from '@/components/envelopes/BudgetSummaryPanel.vue'
import EnvelopeActionSheet from '@/components/envelopes/EnvelopeActionSheet.vue'
import type { AllocationRuleFormData } from '@/components/allocation-rules/AllocationRuleForm.vue'
import type { EnvelopeBudgetItem } from '@/api/envelopes'
import { previewAllocationRules, applyAllocationRules } from '@/api/allocationRules'
import { checkBalanceIntegrity } from '@/api/budgets'
import { recalculateBalances } from '@/api/accounts'
import { recalculateEnvelopeBalances } from '@/api/envelopes'
import { openNewTransaction } from '@/composables/useGlobalTransactionDialog'
import type { Envelope } from '@/types'
import type { RulePreviewResponse } from '@/api/allocationRules'

const router = useRouter()
const envelopesStore = useEnvelopesStore()
const allocationRulesStore = useAllocationRulesStore()
const authStore = useAuthStore()

// Transfer dialog state
const showTransferDialog = ref(false)
const transferFromId = ref<string | null>(null)
const transferToId = ref<string | null>(null)
const transferAmount = ref('')
const transferring = ref(false)
const transferDirection = ref<'from' | 'to'>('to')
const transferContextEnvelopeId = ref<string | null>(null)

// Create envelope dialog state
const showCreateDialog = ref(false)
const newEnvelopeName = ref('')
const newEnvelopeIcon = ref('')
const newEnvelopeGroupId = ref<string | null>(null)
const newEnvelopeTargetBalance = ref('')
const creating = ref(false)
const createWithRule = ref(false)

// Create group dialog state
const showCreateGroupDialog = ref(false)
const newGroupName = ref('')
const creatingGroup = ref(false)

// Inline group creation state (in create envelope dialog)
const isCreatingNewGroup = ref(false)
const inlineNewGroupName = ref('')

// Watch for group selection to show/hide inline group creation
watch(newEnvelopeGroupId, (newValue) => {
  isCreatingNewGroup.value = newValue === '__create_new__'
  if (newValue !== '__create_new__') {
    inlineNewGroupName.value = ''
  }
})

// Create rule dialog state
const showRuleDialog = ref(false)
const ruleEnvelopeId = ref<string | null>(null)
const creatingRule = ref(false)

// Collapse state - stores IDs of collapsed sections
const collapsedSections = ref<Set<string>>(new Set())
const COLLAPSE_STORAGE_KEY = 'budge:envelopes:collapsed'

// Inline rule form in create envelope dialog
const inlineRuleFormRef = ref<InstanceType<typeof AllocationRuleForm> | null>(null)
const inlineRuleType = ref<string>('fixed')
const inlineRuleFormValid = ref(false)

// Auto-assign dialog state
const showAutoAssignDialog = ref(false)
const autoAssignPreview = ref<RulePreviewResponse | null>(null)
const autoAssignLoading = ref(false)
const autoAssigning = ref(false)

// Activity dialog state
const showActivityDialog = ref(false)
const activityEnvelopeId = ref<string | null>(null)
const activityEnvelopeName = ref('')

// Mobile action sheet state
const showActionSheet = ref(false)
const actionSheetEnvelope = ref<EnvelopeBudgetItem | null>(null)
const isMobile = ref(false)

// Balance repair state
const needsRepair = ref(false)
const repairing = ref(false)

// Detect mobile viewport
function checkMobile() {
  isMobile.value = window.innerWidth <= 600
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  // Load collapse state from localStorage
  const budgetId = authStore.currentBudgetId
  if (budgetId) {
    try {
      const stored = localStorage.getItem(COLLAPSE_STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        if (data.budgetId === budgetId && Array.isArray(data.collapsed)) {
          collapsedSections.value = new Set(data.collapsed)
        }
      }
    } catch {
      // Ignore invalid data
    }
  }

  try {
    const budgetId = authStore.currentBudgetId
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      allocationRulesStore.fetchAllocationRules(),
      envelopesStore.fetchBudgetSummary(),
      budgetId
        ? checkBalanceIntegrity(budgetId).then((r) => {
            needsRepair.value = r.needs_repair
          })
        : Promise.resolve(),
    ])
  } catch {
    showSnackbar('Failed to load data', 'error')
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

// Refetch budget summary when date range changes
watch(
  () => envelopesStore.dateRange,
  async () => {
    try {
      await envelopesStore.fetchBudgetSummary()
    } catch {
      showSnackbar('Failed to load budget summary', 'error')
    }
  },
  { deep: true }
)

// Persist collapse state to localStorage on change
watch(
  collapsedSections,
  (newValue) => {
    const budgetId = authStore.currentBudgetId
    if (budgetId) {
      try {
        localStorage.setItem(
          COLLAPSE_STORAGE_KEY,
          JSON.stringify({
            budgetId,
            collapsed: Array.from(newValue),
          })
        )
      } catch {
        // Quota exceeded - fail silently
      }
    }
  },
  { deep: true }
)

// Toggle section collapse state
function toggleSection(sectionId: string) {
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(sectionId)) {
    newSet.delete(sectionId)
  } else {
    newSet.add(sectionId)
  }
  collapsedSections.value = newSet
}

// Check if a section is collapsed
function isSectionCollapsed(sectionId: string): boolean {
  return collapsedSections.value.has(sectionId)
}

const unallocatedEnvelope = computed(() => {
  return envelopesStore.envelopes.find((e) => e.is_unallocated)
})

// Starred budget items for Favorites section
const starredBudgetItems = computed(() => {
  if (!envelopesStore.budgetSummary) return []
  const starred: typeof envelopesStore.budgetSummary.groups[0]['envelopes'] = []
  for (const group of envelopesStore.budgetSummary.groups) {
    for (const item of group.envelopes) {
      if (item.is_starred) {
        starred.push(item)
      }
    }
  }
  return starred
})

const groupOptions = computed(() => [
  { title: 'No Group', value: null },
  ...envelopesStore.envelopeGroups.map((g) => ({ title: g.name, value: g.id })),
  { title: '+ Create New Group', value: '__create_new__' },
])

function openTransferDialog(envelope: Envelope) {
  transferContextEnvelopeId.value = envelope.id
  transferDirection.value = 'to'
  transferFromId.value = null
  transferToId.value = envelope.id
  transferAmount.value = ''
  showTransferDialog.value = true
}

function openTransferFromUnallocated() {
  if (unallocatedEnvelope.value) {
    transferContextEnvelopeId.value = null
    transferFromId.value = unallocatedEnvelope.value.id
    transferToId.value = null
    transferAmount.value = ''
    showTransferDialog.value = true
  }
}

function openTransferToEnvelope(envelopeId: string) {
  transferContextEnvelopeId.value = null
  transferFromId.value = null
  transferToId.value = envelopeId

  // Auto-fill the amount with the overspent amount (absolute value)
  const envelope = envelopesStore.getEnvelopeById(envelopeId)
  if (envelope && envelope.current_balance < 0) {
    const overspentAmount = Math.abs(envelope.current_balance) / 100
    transferAmount.value = overspentAmount.toFixed(2)
  } else {
    transferAmount.value = ''
  }

  showTransferDialog.value = true
}

// Watch for transfer direction toggle changes
watch(transferDirection, (newDirection) => {
  if (!transferContextEnvelopeId.value) return
  if (newDirection === 'to') {
    transferFromId.value = null
    transferToId.value = transferContextEnvelopeId.value
  } else {
    transferFromId.value = transferContextEnvelopeId.value
    transferToId.value = null
  }
})

// Reset context when dialog closes
watch(showTransferDialog, (isOpen) => {
  if (!isOpen) {
    transferContextEnvelopeId.value = null
  }
})

// Cap transfer amount to source envelope's available balance
watch(transferFromId, (newFromId) => {
  if (!newFromId || !transferAmount.value) return

  const sourceEnvelope = envelopesStore.getEnvelopeById(newFromId)
  if (!sourceEnvelope) return

  // Source balance (in cents)
  const sourceBalance = sourceEnvelope.current_balance
  // Can only transfer positive balance
  if (sourceBalance <= 0) {
    transferAmount.value = '0.00'
    return
  }

  const currentAmountCents = Math.round(parseFloat(transferAmount.value) * 100)
  if (currentAmountCents > sourceBalance) {
    transferAmount.value = (sourceBalance / 100).toFixed(2)
  }
})

async function handleTransfer() {
  if (!transferFromId.value || !transferToId.value || !transferAmount.value) return

  const amountCents = Math.round(parseFloat(transferAmount.value) * 100)
  if (amountCents <= 0) {
    showSnackbar('Amount must be greater than 0', 'error')
    return
  }

  try {
    transferring.value = true
    await envelopesStore.transferBetweenEnvelopes(
      transferFromId.value,
      transferToId.value,
      amountCents
    )
    showTransferDialog.value = false
  } catch {
    showSnackbar('Failed to transfer', 'error')
  } finally {
    transferring.value = false
  }
}

async function handleCreateEnvelope() {
  if (!newEnvelopeName.value.trim()) return

  // Validate rule form if toggle is enabled
  if (createWithRule.value && inlineRuleFormRef.value) {
    if (!inlineRuleFormRef.value.isValid()) {
      showSnackbar('Please complete the allocation rule fields', 'error')
      return
    }
  }

  try {
    creating.value = true
    const targetBalance = newEnvelopeTargetBalance.value
      ? Math.round(parseFloat(newEnvelopeTargetBalance.value) * 100)
      : null

    // Step 1: Create new group if requested
    let groupId: string | null = null
    if (isCreatingNewGroup.value && inlineNewGroupName.value.trim()) {
      const group = await envelopesStore.createEnvelopeGroup({
        name: inlineNewGroupName.value.trim(),
      })
      groupId = group.id
    } else if (newEnvelopeGroupId.value !== '__create_new__') {
      groupId = newEnvelopeGroupId.value
    }

    // Step 2: Create the envelope
    const envelope = await envelopesStore.createEnvelope({
      name: newEnvelopeName.value.trim(),
      envelope_group_id: groupId,
      target_balance: targetBalance,
      icon: newEnvelopeIcon.value.trim() || null,
    })

    // Step 3: Create allocation rule if toggle is enabled
    if (createWithRule.value && inlineRuleFormRef.value) {
      const ruleData = inlineRuleFormRef.value.getFormData()
      if (ruleData) {
        try {
          await allocationRulesStore.createAllocationRule({
            ...ruleData,
            envelope_id: envelope.id,
          })
        } catch {
          showSnackbar(
            'Envelope created, but allocation rule failed. You can add a rule later.',
            'warning'
          )
        }
      }
    }

    // Refresh the envelopes list (to get unallocated envelope) and budget summary
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      envelopesStore.fetchBudgetSummary(),
    ])
  } catch {
    showSnackbar('Failed to create envelope', 'error')
  } finally {
    // ALWAYS close dialog and reset form, even on error
    showCreateDialog.value = false
    newEnvelopeName.value = ''
    newEnvelopeIcon.value = ''
    newEnvelopeGroupId.value = null
    newEnvelopeTargetBalance.value = ''
    createWithRule.value = false
    isCreatingNewGroup.value = false
    inlineNewGroupName.value = ''
    creating.value = false
  }
}

async function handleCreateGroup() {
  if (!newGroupName.value.trim()) return

  try {
    creatingGroup.value = true
    await envelopesStore.createEnvelopeGroup({
      name: newGroupName.value.trim(),
    })
    // Refresh budget summary to show the new group
    await envelopesStore.fetchBudgetSummary()
  } catch {
    showSnackbar('Failed to create group', 'error')
  } finally {
    // ALWAYS close dialog and reset form, even on error
    showCreateGroupDialog.value = false
    newGroupName.value = ''
    creatingGroup.value = false
  }
}

// Allocation rule helpers
function getNextRulePriority(): number {
  const rules = allocationRulesStore.sortedRules
  if (rules.length === 0) return 10
  const maxPriority = Math.max(...rules.map((r) => r.priority))
  return maxPriority + 10
}

async function handleCreateRuleFromForm(data: AllocationRuleFormData) {
  if (!ruleEnvelopeId.value) return

  try {
    creatingRule.value = true
    await allocationRulesStore.createAllocationRule({
      ...data,
      envelope_id: ruleEnvelopeId.value,
    })
    showRuleDialog.value = false
  } catch {
    showSnackbar('Failed to create rule', 'error')
  } finally {
    creatingRule.value = false
  }
}

const transferFromName = computed(() => {
  if (!transferFromId.value) return ''
  const envelope = envelopesStore.getEnvelopeById(transferFromId.value)
  return envelope?.is_unallocated ? 'Unallocated' : envelope?.name || ''
})

const transferToName = computed(() => {
  if (!transferToId.value) return ''
  const envelope = envelopesStore.getEnvelopeById(transferToId.value)
  return envelope?.is_unallocated ? 'Unallocated' : envelope?.name || ''
})

const transferContextEnvelopeName = computed(() => {
  if (!transferContextEnvelopeId.value) return ''
  const envelope = envelopesStore.getEnvelopeById(transferContextEnvelopeId.value)
  return envelope?.is_unallocated ? 'Unallocated' : envelope?.name || ''
})

const hasActiveRules = computed(() => {
  return allocationRulesStore.activeRules.length > 0
})

// Warning when fill_to_target rule is selected but no target balance set
const showFillToTargetWarning = computed(() => {
  if (!createWithRule.value) return false

  const hasTargetBalance = newEnvelopeTargetBalance.value && parseFloat(newEnvelopeTargetBalance.value) > 0
  return inlineRuleType.value === 'fill_to_target' && !hasTargetBalance
})

// Check if envelope name already exists (case-insensitive)
const envelopeNameExists = computed(() => {
  const name = newEnvelopeName.value.trim().toLowerCase()
  if (!name) return false
  return envelopesStore.envelopes.some((e) => e.name.toLowerCase() === name)
})

// Check if group name already exists (case-insensitive)
const groupNameExists = computed(() => {
  const name = inlineNewGroupName.value.trim().toLowerCase()
  if (!name) return false
  return envelopesStore.envelopeGroups.some((g) => g.name.toLowerCase() === name)
})

// Computed for create envelope button disabled state
const isCreateEnvelopeDisabled = computed(() => {
  if (!newEnvelopeName.value.trim()) return true

  // Check for duplicate envelope name
  if (envelopeNameExists.value) return true

  // If creating a new group, require the group name and check for duplicates
  if (isCreatingNewGroup.value) {
    if (!inlineNewGroupName.value.trim()) return true
    if (groupNameExists.value) return true
  }

  // If rule toggle is on, check rule form validity and fill_to_target warning
  if (createWithRule.value) {
    // Check fill_to_target warning first (it's reactive via inlineRuleType)
    if (showFillToTargetWarning.value) return true

    // Check form validity via the emit-tracked state
    if (!inlineRuleFormValid.value) return true
  }

  return false
})

// Update rule type when form emits change
function handleRuleTypeChange(ruleType: string) {
  inlineRuleType.value = ruleType
}

async function openAutoAssignDialog() {
  if (!unallocatedEnvelope.value || !authStore.currentBudgetId) return

  showAutoAssignDialog.value = true
  autoAssignPreview.value = null
  autoAssignLoading.value = true

  try {
    autoAssignPreview.value = await previewAllocationRules(authStore.currentBudgetId, {
      amount: unallocatedEnvelope.value.current_balance,
    })
  } catch {
    showSnackbar('Failed to load preview', 'error')
    showAutoAssignDialog.value = false
  } finally {
    autoAssignLoading.value = false
  }
}

async function handleAutoAssign() {
  if (!authStore.currentBudgetId) return

  try {
    autoAssigning.value = true
    await applyAllocationRules(authStore.currentBudgetId)
    showAutoAssignDialog.value = false
    await Promise.all([envelopesStore.fetchEnvelopes(), envelopesStore.fetchBudgetSummary()])
  } catch {
    showSnackbar('Failed to assign money', 'error')
  } finally {
    autoAssigning.value = false
  }
}

function getEnvelopeNameById(envelopeId: string): string {
  const envelope = envelopesStore.getEnvelopeById(envelopeId)
  return envelope?.name || 'Unknown'
}

// Edit mode handlers
async function handleToggleEditMode() {
  if (!envelopesStore.isEditMode) {
    // Entering edit mode - initialize sort orders if needed
    try {
      await envelopesStore.initializeSortOrders()
    } catch {
      showSnackbar('Failed to initialize ordering', 'error')
      return
    }
  }
  envelopesStore.toggleEditMode()
}

async function handleMoveEnvelopeUp(envelopeId: string) {
  try {
    await envelopesStore.moveEnvelopeUp(envelopeId)
    await envelopesStore.fetchBudgetSummary()
  } catch {
    showSnackbar('Failed to reorder envelope', 'error')
  }
}

async function handleMoveEnvelopeDown(envelopeId: string) {
  try {
    await envelopesStore.moveEnvelopeDown(envelopeId)
    await envelopesStore.fetchBudgetSummary()
  } catch {
    showSnackbar('Failed to reorder envelope', 'error')
  }
}

async function handleMoveGroupUp(groupId: string) {
  try {
    await envelopesStore.moveGroupUp(groupId)
    await envelopesStore.fetchBudgetSummary()
  } catch {
    showSnackbar('Failed to reorder group', 'error')
  }
}

async function handleMoveGroupDown(groupId: string) {
  try {
    await envelopesStore.moveGroupDown(groupId)
    await envelopesStore.fetchBudgetSummary()
  } catch {
    showSnackbar('Failed to reorder group', 'error')
  }
}

// Date range handlers
function handleDateRangePreset(preset: DateRangePreset) {
  envelopesStore.setDateRange(preset)
}

function handleCustomDateRange(startDate: string, endDate: string) {
  envelopesStore.setDateRange('custom', startDate, endDate)
}

// Activity dialog handler
function openActivityDialog(item: EnvelopeBudgetItem) {
  activityEnvelopeId.value = item.envelope_id
  activityEnvelopeName.value = item.envelope_name
  showActivityDialog.value = true
}

// Inline balance edit handler - transfers difference to/from Unallocated
async function handleBalanceSave(item: EnvelopeBudgetItem, newBalance: number) {
  const unallocated = envelopesStore.unallocatedEnvelope
  if (!unallocated) {
    showSnackbar('Unallocated envelope not found', 'error')
    return
  }

  const diff = newBalance - item.balance
  if (diff === 0) return

  try {
    if (diff > 0) {
      // Transferring TO this envelope FROM unallocated
      await envelopesStore.transferBetweenEnvelopes(unallocated.id, item.envelope_id, diff)
    } else {
      // Transferring FROM this envelope TO unallocated
      await envelopesStore.transferBetweenEnvelopes(item.envelope_id, unallocated.id, Math.abs(diff))
    }
  } catch {
    showSnackbar('Failed to update balance', 'error')
  }
}

// Budget row handlers
function handleBudgetRowClick(item: EnvelopeBudgetItem) {
  if (envelopesStore.isEditMode) return

  if (isMobile.value) {
    // On mobile, show action sheet instead of navigating
    actionSheetEnvelope.value = item
    showActionSheet.value = true
  } else {
    // On desktop, navigate to envelope detail
    router.push(`/envelopes/${item.envelope_id}`)
  }
}

function handleBudgetRowTransfer(item: EnvelopeBudgetItem) {
  const envelope = envelopesStore.getEnvelopeById(item.envelope_id)
  if (envelope) {
    openTransferDialog(envelope)
  }
}

function handleBudgetRowAddTransaction(item: EnvelopeBudgetItem) {
  openNewTransaction(null, item.envelope_id)
}

// Action sheet handlers
function handleActionSheetTransfer() {
  if (actionSheetEnvelope.value) {
    handleBudgetRowTransfer(actionSheetEnvelope.value)
  }
  showActionSheet.value = false
}

function handleActionSheetAddTransaction() {
  if (actionSheetEnvelope.value) {
    handleBudgetRowAddTransaction(actionSheetEnvelope.value)
  }
  showActionSheet.value = false
}

function handleActionSheetViewActivity() {
  if (actionSheetEnvelope.value) {
    openActivityDialog(actionSheetEnvelope.value)
  }
  showActionSheet.value = false
}

function handleActionSheetViewDetails() {
  if (actionSheetEnvelope.value) {
    router.push(`/envelopes/${actionSheetEnvelope.value.envelope_id}`)
  }
  showActionSheet.value = false
}

async function handleRepair() {
  const budgetId = authStore.currentBudgetId
  if (!budgetId) return

  try {
    repairing.value = true
    await recalculateBalances(budgetId)
    await recalculateEnvelopeBalances(budgetId)
    showSnackbar('Balances repaired successfully')

    // Re-check and refresh data
    const [checkResult] = await Promise.all([
      checkBalanceIntegrity(budgetId),
      envelopesStore.fetchEnvelopes(),
      envelopesStore.fetchBudgetSummary(),
    ])
    needsRepair.value = checkResult.needs_repair
  } catch {
    showSnackbar('Failed to repair balances', 'error')
  } finally {
    repairing.value = false
  }
}
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <h1 class="text-h4">
        Envelopes
      </h1>

      <!-- Settings menu (gear icon) -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn
            icon
            variant="text"
            size="small"
            v-bind="props"
          >
            <v-icon>mdi-cog</v-icon>
          </v-btn>
        </template>
        <v-list>
          <v-list-item @click="showCreateDialog = true">
            <template #prepend>
              <v-icon>mdi-email-plus-outline</v-icon>
            </template>
            <v-list-item-title>Add Envelope</v-list-item-title>
          </v-list-item>
          <v-list-item @click="showCreateGroupDialog = true">
            <template #prepend>
              <v-icon>mdi-folder-plus-outline</v-icon>
            </template>
            <v-list-item-title>Add Envelope Group</v-list-item-title>
          </v-list-item>
          <v-divider />
          <v-list-item
            :disabled="envelopesStore.reorderLoading"
            @click="handleToggleEditMode"
          >
            <template #prepend>
              <v-icon>{{ envelopesStore.isEditMode ? 'mdi-check' : 'mdi-pencil' }}</v-icon>
            </template>
            <v-list-item-title>{{ envelopesStore.isEditMode ? 'Done Editing' : 'Edit Order' }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-spacer />

      <!-- Date Range Picker -->
      <DateRangePicker
        :start-date="envelopesStore.dateRange.startDate"
        :end-date="envelopesStore.dateRange.endDate"
        :preset="envelopesStore.dateRange.preset"
        @update:preset="handleDateRangePreset"
        @update:custom-range="handleCustomDateRange"
      />
    </div>

    <!-- Balance Repair Alert -->
    <BalanceRepairAlert
      :needs-repair="needsRepair"
      :loading="repairing"
      @repair="handleRepair"
    />

    <!-- Unallocated Balance Card -->
    <v-card
      v-if="unallocatedEnvelope"
      class="mb-4"
      :color="unallocatedEnvelope.current_balance > 0 ? 'success' : unallocatedEnvelope.current_balance < 0 ? 'error' : undefined"
      :variant="unallocatedEnvelope.current_balance !== 0 ? 'tonal' : 'outlined'"
    >
      <v-card-text class="d-flex align-center justify-space-between">
        <div>
          <div class="text-subtitle-2 text-medium-emphasis">
            Ready to Assign
          </div>
          <MoneyDisplay
            :amount="unallocatedEnvelope.current_balance"
            class="text-h5 font-weight-bold"
          />
        </div>
        <v-menu v-if="unallocatedEnvelope.current_balance > 0">
          <template #activator="{ props }">
            <v-btn
              variant="tonal"
              v-bind="props"
            >
              Assign Money
              <v-icon end>
                mdi-chevron-down
              </v-icon>
            </v-btn>
          </template>
          <v-list>
            <v-list-item @click="openTransferFromUnallocated">
              <template #prepend>
                <v-icon>mdi-hand-coin-outline</v-icon>
              </template>
              <v-list-item-title>Assign Manually</v-list-item-title>
            </v-list-item>
            <v-list-item
              :disabled="!hasActiveRules"
              @click="openAutoAssignDialog"
            >
              <template #prepend>
                <v-icon>mdi-auto-fix</v-icon>
              </template>
              <v-list-item-title>Auto-Assign with Rules</v-list-item-title>
              <v-list-item-subtitle v-if="!hasActiveRules">
                No allocation rules configured
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-card-text>
    </v-card>

    <!-- Overspent Alert -->
    <OverspentAlert @cover-envelope="openTransferToEnvelope" />

    <!-- Loading State -->
    <div
      v-if="envelopesStore.loading && envelopesStore.envelopes.length === 0"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <!-- Empty State -->
    <v-card v-else-if="envelopesStore.activeEnvelopes.length === 0">
      <v-card-text class="text-center text-grey py-8">
        <v-icon
          size="64"
          color="grey-lighten-1"
        >
          mdi-wallet-outline
        </v-icon>
        <p class="mt-4">
          No envelopes yet. Create envelopes to organize your budget!
        </p>
        <v-btn
          color="primary"
          class="mt-4"
          @click="showCreateDialog = true"
        >
          Create Envelope
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- Main Content Area -->
    <template v-else>
      <v-row>
        <!-- Main Column -->
        <v-col
          cols="12"
          lg="9"
        >
          <!-- Budget View -->
          <template v-if="envelopesStore.budgetSummary">
            <!-- Column Headers -->
            <div class="budget-column-headers d-flex align-center px-4 py-2 mb-2">
              <div class="flex-grow-1" />
              <div class="budget-header-col activity-col text-caption text-medium-emphasis text-right">
                Activity
              </div>
              <div class="budget-header-col text-caption text-medium-emphasis text-right">
                Balance
              </div>
              <div class="budget-header-actions" />
            </div>

            <!-- Favorites Section -->
            <div
              v-if="starredBudgetItems.length > 0"
              class="mb-4"
            >
              <!-- Favorites Header -->
              <div
                class="d-flex align-center mb-2 px-2 envelope-group-header"
                @click="toggleSection('favorites')"
              >
                <v-icon
                  size="small"
                  class="mr-1 collapse-chevron"
                  :class="{ 'rotate-collapsed': isSectionCollapsed('favorites') }"
                >
                  mdi-chevron-down
                </v-icon>
                <v-icon
                  size="small"
                  class="mr-2"
                  color="amber"
                >
                  mdi-star
                </v-icon>
                <span class="text-subtitle-2 text-grey">Favorites</span>
              </div>

              <!-- Favorites Envelopes -->
              <v-expand-transition>
                <v-card v-show="!isSectionCollapsed('favorites')">
                  <v-list density="compact">
                    <EnvelopeBudgetRow
                      v-for="(item, itemIndex) in starredBudgetItems"
                      :key="item.envelope_id"
                      :item="item"
                      :edit-mode="envelopesStore.isEditMode"
                      :is-first="itemIndex === 0"
                      :is-last="itemIndex === starredBudgetItems.length - 1"
                      :reorder-loading="envelopesStore.reorderLoading"
                      @click="handleBudgetRowClick(item)"
                      @transfer="handleBudgetRowTransfer(item)"
                      @add-transaction="handleBudgetRowAddTransaction(item)"
                      @activity-click="openActivityDialog(item)"
                      @balance-save="(val) => handleBalanceSave(item, val)"
                      @move-up="handleMoveEnvelopeUp(item.envelope_id)"
                      @move-down="handleMoveEnvelopeDown(item.envelope_id)"
                    />
                  </v-list>
                </v-card>
              </v-expand-transition>
            </div>

            <!-- Budget Groups from Summary -->
            <div
              v-for="group in envelopesStore.budgetSummary.groups"
              :key="group.group_id || 'ungrouped'"
              class="mb-4"
            >
              <!-- Group Header -->
              <div
                class="d-flex align-center mb-2 px-2 envelope-group-header"
                @click="toggleSection(group.group_id || 'ungrouped')"
              >
                <v-icon
                  size="small"
                  class="mr-1 collapse-chevron"
                  :class="{ 'rotate-collapsed': isSectionCollapsed(group.group_id || 'ungrouped') }"
                >
                  mdi-chevron-down
                </v-icon>
                <v-icon
                  size="small"
                  class="mr-2"
                >
                  {{ group.icon || 'mdi-folder-outline' }}
                </v-icon>
                <span class="text-subtitle-2 text-grey">{{ group.group_name || 'Other' }}</span>

                <!-- Group totals -->
                <v-spacer />
                <div class="d-flex align-center text-caption text-medium-emphasis">
                  <MoneyDisplay
                    :amount="group.total_balance"
                    size="small"
                    :colored="false"
                  />
                </div>

                <!-- Group reorder buttons in edit mode -->
                <template v-if="envelopesStore.isEditMode && group.group_id">
                  <v-btn
                    icon="mdi-chevron-up"
                    size="x-small"
                    variant="text"
                    :disabled="envelopesStore.isGroupFirst(group.group_id) || envelopesStore.reorderLoading"
                    @click.stop="handleMoveGroupUp(group.group_id)"
                  />
                  <v-btn
                    icon="mdi-chevron-down"
                    size="x-small"
                    variant="text"
                    :disabled="envelopesStore.isGroupLast(group.group_id) || envelopesStore.reorderLoading"
                    @click.stop="handleMoveGroupDown(group.group_id)"
                  />
                </template>
              </div>

              <!-- Group Envelopes -->
              <v-expand-transition>
                <v-card v-show="!isSectionCollapsed(group.group_id || 'ungrouped')">
                  <v-list density="compact">
                    <EnvelopeBudgetRow
                      v-for="(item, itemIndex) in group.envelopes"
                      :key="item.envelope_id"
                      :item="item"
                      :edit-mode="envelopesStore.isEditMode"
                      :is-first="itemIndex === 0"
                      :is-last="itemIndex === group.envelopes.length - 1"
                      :reorder-loading="envelopesStore.reorderLoading"
                      @click="handleBudgetRowClick(item)"
                      @transfer="handleBudgetRowTransfer(item)"
                      @add-transaction="handleBudgetRowAddTransaction(item)"
                      @activity-click="openActivityDialog(item)"
                      @balance-save="(val) => handleBalanceSave(item, val)"
                      @move-up="handleMoveEnvelopeUp(item.envelope_id)"
                      @move-down="handleMoveEnvelopeDown(item.envelope_id)"
                    />
                  </v-list>
                </v-card>
              </v-expand-transition>
            </div>
          </template>
        </v-col>

        <!-- Summary Panel -->
        <v-col
          cols="12"
          lg="3"
          class="d-none d-lg-block"
        >
          <BudgetSummaryPanel />
        </v-col>
      </v-row>
    </template>

    <!-- Activity Dialog -->
    <EnvelopeActivityDialog
      v-model="showActivityDialog"
      :envelope-id="activityEnvelopeId"
      :envelope-name="activityEnvelopeName"
    />

    <!-- Mobile Action Sheet -->
    <EnvelopeActionSheet
      v-model="showActionSheet"
      :envelope="actionSheetEnvelope"
      :is-credit-card="actionSheetEnvelope?.linked_account_id !== null"
      @transfer="handleActionSheetTransfer"
      @add-transaction="handleActionSheetAddTransaction"
      @view-activity="handleActionSheetViewActivity"
      @view-details="handleActionSheetViewDetails"
    />

    <!-- Transfer Dialog -->
    <v-dialog
      v-model="showTransferDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Transfer Money</v-card-title>
        <v-card-text>
          <!-- Direction Toggle: Only show when opened from envelope card -->
          <v-btn-toggle
            v-if="transferContextEnvelopeId"
            v-model="transferDirection"
            mandatory
            density="compact"
            class="mb-4 d-flex"
          >
            <v-btn
              value="to"
              class="flex-grow-1"
            >
              To {{ transferContextEnvelopeName }}
            </v-btn>
            <v-btn
              value="from"
              class="flex-grow-1"
            >
              From {{ transferContextEnvelopeName }}
            </v-btn>
          </v-btn-toggle>

          <div class="form-fields">
            <!-- Mode 1: Source is pre-selected (transfer OUT) -->
            <template v-if="transferFromId && !transferToId">
              <p
                v-if="!transferContextEnvelopeId"
                class="text-body-2 mb-4"
              >
                Moving money from <strong>{{ transferFromName }}</strong>
              </p>

              <EnvelopeSelect
                v-model="transferToId"
                label="To Envelope"
                grouped
                show-balances
                include-credit-cards
                :exclude-ids="transferFromId ? [transferFromId] : []"
              />
            </template>

            <!-- Mode 2: Destination is pre-selected (transfer INTO or covering overspending) -->
            <template v-else-if="transferToId && !transferFromId">
              <p
                v-if="!transferContextEnvelopeId"
                class="text-body-2 mb-4"
              >
                Cover overspending in <strong>{{ transferToName }}</strong>
              </p>

              <EnvelopeSelect
                v-model="transferFromId"
                label="From Envelope"
                grouped
                show-balances
                include-credit-cards
                :exclude-ids="transferToId ? [transferToId] : []"
              />
            </template>

            <!-- Mode 3: Both selected (shouldn't normally happen) -->
            <template v-else>
              <p class="text-body-2 mb-4">
                Moving money from <strong>{{ transferFromName }}</strong> to <strong>{{ transferToName }}</strong>
              </p>
            </template>

            <MoneyInput
              v-model="transferAmount"
              label="Amount"
            />
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showTransferDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="transferring"
            :disabled="!transferFromId || !transferToId || !transferAmount || parseFloat(transferAmount) <= 0"
            @click="handleTransfer"
          >
            Transfer
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create Envelope Dialog -->
    <v-dialog
      v-model="showCreateDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Create Envelope</v-card-title>
        <v-card-text>
          <div class="form-fields">
            <v-text-field
              v-model="newEnvelopeName"
              label="Envelope Name"
              autofocus
              :error="envelopeNameExists"
              :error-messages="envelopeNameExists ? 'An envelope with this name already exists' : undefined"
            />

            <v-text-field
              v-model="newEnvelopeIcon"
              label="Icon (emoji)"
              placeholder="🛒"
              hint="Optional - tap to open emoji keyboard"
              persistent-hint
              style="max-width: 120px"
            />

            <v-select
              v-model="newEnvelopeGroupId"
              label="Group (optional)"
              :items="groupOptions"
              clearable
            />

            <v-text-field
              v-if="isCreatingNewGroup"
              v-model="inlineNewGroupName"
              label="New Group Name"
              :error="groupNameExists"
              :error-messages="groupNameExists ? 'A group with this name already exists' : undefined"
            />

            <v-text-field
              v-model="newEnvelopeTargetBalance"
              label="Target Balance (optional)"
              type="number"
              step="0.01"
              min="0"
              prefix="$"
              hint="Set a goal amount for this envelope"
              persistent-hint
            />

            <v-divider class="my-4" />

            <v-switch
              v-model="createWithRule"
              label="Add allocation rule"
              hint="Automatically allocate money to this envelope"
              persistent-hint
            />

            <template v-if="createWithRule">
              <v-alert
                v-if="showFillToTargetWarning"
                type="warning"
                variant="tonal"
                density="compact"
              >
                Fill to Target requires a target balance to be set above.
              </v-alert>

              <AllocationRuleForm
                ref="inlineRuleFormRef"
                :default-name="newEnvelopeName"
                :show-envelope-select="false"
                :show-actions="false"
                :default-priority="getNextRulePriority()"
                @update:valid="inlineRuleFormValid = $event"
                @update:rule-type="handleRuleTypeChange"
              />
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showCreateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="creating"
            :disabled="isCreateEnvelopeDisabled"
            @click="handleCreateEnvelope"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create Group Dialog -->
    <v-dialog
      v-model="showCreateGroupDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Create Group</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newGroupName"
            label="Group Name"
            autofocus
            @keyup.enter="handleCreateGroup"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showCreateGroupDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="creatingGroup"
            :disabled="!newGroupName.trim()"
            @click="handleCreateGroup"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create Allocation Rule Dialog -->
    <v-dialog
      v-model="showRuleDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>New Allocation Rule</v-card-title>
        <v-card-text>
          <AllocationRuleForm
            :envelope-id="ruleEnvelopeId"
            :default-name="ruleEnvelopeId ? getEnvelopeNameById(ruleEnvelopeId) : null"
            :show-envelope-select="false"
            :loading="creatingRule"
            :default-priority="getNextRulePriority()"
            @submit="handleCreateRuleFromForm"
            @cancel="showRuleDialog = false"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Auto-Assign Preview Dialog -->
    <v-dialog
      v-model="showAutoAssignDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>Auto-Assign Money</v-card-title>
        <v-card-text>
          <div
            v-if="unallocatedEnvelope"
            class="mb-4"
          >
            <div class="text-subtitle-2 text-medium-emphasis">
              Ready to Assign
            </div>
            <MoneyDisplay
              :amount="unallocatedEnvelope.current_balance"
              class="text-h5 font-weight-bold"
            />
          </div>

          <v-divider class="mb-4" />

          <div
            v-if="autoAssignLoading"
            class="text-center py-4"
          >
            <v-progress-circular
              indeterminate
              color="primary"
            />
            <p class="mt-2 text-medium-emphasis">
              Loading preview...
            </p>
          </div>

          <div v-else-if="autoAssignPreview">
            <div v-if="autoAssignPreview.allocations.length > 0">
              <div class="text-subtitle-2 mb-2">
                Planned Allocations
              </div>
              <v-list density="compact">
                <v-list-item
                  v-for="alloc in autoAssignPreview.allocations"
                  :key="alloc.envelope_id"
                >
                  <template #prepend>
                    <v-icon
                      size="small"
                      color="success"
                    >
                      mdi-arrow-right
                    </v-icon>
                  </template>
                  <v-list-item-title>{{ getEnvelopeNameById(alloc.envelope_id) }}</v-list-item-title>
                  <v-list-item-subtitle v-if="alloc.rule_name">
                    {{ alloc.rule_name }}
                  </v-list-item-subtitle>
                  <template #append>
                    <MoneyDisplay
                      :amount="alloc.amount"
                      class="font-weight-medium"
                    />
                  </template>
                </v-list-item>
              </v-list>

              <v-alert
                v-if="autoAssignPreview.unallocated > 0"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-4"
              >
                <MoneyDisplay
                  :amount="autoAssignPreview.unallocated"
                  class="font-weight-medium"
                />
                will remain unallocated
              </v-alert>
            </div>
            <div
              v-else
              class="text-center py-4 text-medium-emphasis"
            >
              <v-icon
                size="48"
                class="mb-2"
              >
                mdi-information-outline
              </v-icon>
              <p>No allocations would be made.</p>
              <p class="text-body-2">
                All envelopes may be at their target balances.
              </p>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showAutoAssignDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="autoAssigning"
            :disabled="!autoAssignPreview?.allocations.length"
            @click="handleAutoAssign"
          >
            Apply
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.envelope-group-header {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
}

.envelope-group-header:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.collapse-chevron {
  transition: transform 200ms ease-in-out;
}

.rotate-collapsed {
  transform: rotate(-90deg);
}

/* Budget view styles */
.budget-column-headers {
  border-radius: 4px;
}

.budget-header-col {
  width: 100px;
  min-width: 100px;
  padding: 0 8px;
  box-sizing: border-box;
}

.budget-header-actions {
  width: 76px; /* Space for action buttons (2 x 28px + 8px gap + 12px margin) */
  min-width: 76px;
}

@media (max-width: 600px) {
  .budget-header-col {
    width: 80px;
    min-width: 80px;
    padding: 0 2px;
  }

  .budget-header-col.activity-col {
    display: none;
  }

  .budget-header-actions {
    display: none;
  }
}
</style>
