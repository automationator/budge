<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEnvelopesStore } from '@/stores/envelopes'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import { listAllocationsForEnvelope } from '@/api/allocations'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import AllocationRuleForm from '@/components/allocation-rules/AllocationRuleForm.vue'
import type { AllocationRuleFormData } from '@/components/allocation-rules/AllocationRuleForm.vue'
import type { Envelope, Allocation, AllocationRule, AllocationRuleType } from '@/types'

const route = useRoute()
const router = useRouter()
const envelopesStore = useEnvelopesStore()
const allocationRulesStore = useAllocationRulesStore()
const authStore = useAuthStore()

const envelopeId = computed(() => route.params.id as string)
const envelope = ref<Envelope | null>(null)
const allocations = ref<Allocation[]>([])
const loading = ref(false)

// Edit dialog
const showEditDialog = ref(false)
const editName = ref('')
const editIcon = ref('')
const editGroupId = ref<string | null>(null)
const editTargetBalance = ref('')
const editDescription = ref('')
const saving = ref(false)

// Transfer dialog
const showTransferDialog = ref(false)
const transferDirection = ref<'from' | 'to'>('to')
const transferOtherId = ref<string | null>(null)
const transferAmount = ref('')
const transferring = ref(false)

// Delete dialog
const showDeleteDialog = ref(false)
const deleting = ref(false)

// Star toggle
const starring = ref(false)

// Allocation rule dialog
const showRuleDialog = ref(false)
const editingRule = ref<AllocationRule | null>(null)
const savingRule = ref(false)

// Delete rule dialog
const showDeleteRuleDialog = ref(false)
const deletingRuleId = ref<string | null>(null)
const deletingRule = ref(false)

onMounted(async () => {
  await loadEnvelope()
})

async function loadEnvelope() {
  try {
    loading.value = true
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      allocationRulesStore.fetchAllocationRules(),
    ])
    envelope.value = await envelopesStore.fetchEnvelope(envelopeId.value)

    // Load allocations
    if (authStore.currentBudgetId) {
      allocations.value = await listAllocationsForEnvelope(
        authStore.currentBudgetId,
        envelopeId.value
      )
    }
  } catch {
    showSnackbar('Failed to load envelope', 'error')
    router.push('/envelopes')
  } finally {
    loading.value = false
  }
}

const progressPercent = computed(() => {
  if (!envelope.value?.target_balance || envelope.value.target_balance <= 0) {
    return null
  }
  const percent = (envelope.value.current_balance / envelope.value.target_balance) * 100
  return Math.min(Math.max(percent, 0), 100)
})

const progressColor = computed(() => {
  if (progressPercent.value === null) return 'primary'
  if (progressPercent.value >= 100) return 'success'
  if (progressPercent.value >= 50) return 'primary'
  if (progressPercent.value >= 25) return 'warning'
  return 'error'
})

const groupOptions = computed(() => [
  { title: 'No Group', value: null },
  ...envelopesStore.envelopeGroups.map((g) => ({ title: g.name, value: g.id })),
])

const transferableEnvelopes = computed(() => {
  const options = []

  // Add unallocated envelope
  const unallocated = envelopesStore.envelopes.find((e) => e.is_unallocated)
  if (unallocated) {
    options.push({ title: 'Unallocated', value: unallocated.id })
  }

  // Add other envelopes
  for (const e of envelopesStore.activeEnvelopes) {
    if (e.id !== envelopeId.value && !e.is_unallocated) {
      options.push({ title: e.name, value: e.id })
    }
  }

  return options
})

const currentGroup = computed(() => {
  if (!envelope.value?.envelope_group_id) return null
  return envelopesStore.getGroupById(envelope.value.envelope_group_id)
})

function openEditDialog() {
  if (!envelope.value) return
  editName.value = envelope.value.name
  editIcon.value = envelope.value.icon || ''
  editGroupId.value = envelope.value.envelope_group_id
  editTargetBalance.value = envelope.value.target_balance
    ? (envelope.value.target_balance / 100).toFixed(2)
    : ''
  editDescription.value = envelope.value.description || ''
  showEditDialog.value = true
}

async function handleSave() {
  if (!envelope.value || !editName.value.trim()) return

  try {
    saving.value = true
    const targetBalance = editTargetBalance.value
      ? Math.round(parseFloat(editTargetBalance.value) * 100)
      : null

    await envelopesStore.updateEnvelope(envelope.value.id, {
      name: editName.value.trim(),
      icon: editIcon.value.trim() || null,
      envelope_group_id: editGroupId.value,
      target_balance: targetBalance,
      description: editDescription.value || null,
    })

    envelope.value = envelopesStore.getEnvelopeById(envelope.value.id) || envelope.value
    showEditDialog.value = false
  } catch {
    showSnackbar('Failed to update envelope', 'error')
  } finally {
    saving.value = false
  }
}

function openTransferDialog() {
  transferDirection.value = 'to'
  transferOtherId.value = null
  transferAmount.value = ''
  showTransferDialog.value = true
}

async function handleTransfer() {
  if (!envelope.value || !transferOtherId.value || !transferAmount.value) return

  const amountCents = Math.round(parseFloat(transferAmount.value) * 100)
  if (amountCents <= 0) {
    showSnackbar('Amount must be greater than 0', 'error')
    return
  }

  // 'to' mode = transfer INTO current envelope, 'from' mode = transfer OUT of current envelope
  const fromId = transferDirection.value === 'to'
    ? transferOtherId.value
    : envelope.value.id
  const toId = transferDirection.value === 'to'
    ? envelope.value.id
    : transferOtherId.value

  try {
    transferring.value = true
    await envelopesStore.transferBetweenEnvelopes(fromId, toId, amountCents)

    // Refresh envelope
    envelope.value = envelopesStore.getEnvelopeById(envelope.value.id) || envelope.value

    showTransferDialog.value = false
  } catch {
    showSnackbar('Failed to transfer', 'error')
  } finally {
    transferring.value = false
  }
}

async function handleDelete() {
  if (!envelope.value) return

  try {
    deleting.value = true
    await envelopesStore.deleteEnvelope(envelope.value.id)
    router.push('/envelopes')
  } catch {
    showSnackbar('Failed to delete envelope', 'error')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

async function handleToggleStar() {
  if (!envelope.value) return
  try {
    starring.value = true
    await envelopesStore.toggleStarred(envelope.value.id)
    envelope.value = envelopesStore.getEnvelopeById(envelope.value.id) || envelope.value
  } catch {
    showSnackbar('Failed to update star status', 'error')
  } finally {
    starring.value = false
  }
}

function formatAllocationDate(allocation: Allocation): string {
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const parts = allocation.date.split('-')
  const year = parts[0] ?? ''
  const month = parts[1] ?? '01'
  const day = parts[2] ?? '01'
  return `${monthNames[parseInt(month, 10) - 1]} ${parseInt(day, 10)}, ${year}`
}

// Allocation rules computed and helpers
const envelopeRules = computed(() => {
  return allocationRulesStore.rulesByEnvelope[envelopeId.value] || []
})

function getRuleTypeIcon(type: AllocationRuleType): string {
  switch (type) {
    case 'fill_to_target':
      return 'mdi-target'
    case 'fixed':
      return 'mdi-currency-usd'
    case 'percentage':
      return 'mdi-percent'
    case 'remainder':
      return 'mdi-scale-balance'
    case 'period_cap':
      return 'mdi-speedometer'
  }
}

function getRuleTypeLabel(type: AllocationRuleType): string {
  switch (type) {
    case 'fill_to_target':
      return 'Fill to Target'
    case 'fixed':
      return 'Fixed Amount'
    case 'percentage':
      return 'Percentage'
    case 'remainder':
      return 'Remainder'
    case 'period_cap':
      return 'Period Cap'
  }
}

function formatRuleAmount(rule: AllocationRule): string {
  switch (rule.rule_type) {
    case 'fill_to_target':
      return 'To target'
    case 'fixed':
      return `$${(rule.amount / 100).toFixed(2)}`
    case 'percentage':
      return `${(rule.amount / 100).toFixed(1)}%`
    case 'remainder':
      return `Weight: ${rule.amount}`
    case 'period_cap':
      return `$${(rule.amount / 100).toFixed(2)} / ${rule.cap_period_value} ${rule.cap_period_unit}${rule.cap_period_value > 1 ? 's' : ''}`
  }
}

const hasPeriodCap = computed(() => {
  return allocationRulesStore.envelopeHasPeriodCap(
    envelopeId.value,
    editingRule.value?.id
  )
})

const nextRulePriority = computed(() => {
  const rules = allocationRulesStore.sortedRules
  if (rules.length === 0) return 10
  const maxPriority = Math.max(...rules.map((r) => r.priority))
  return maxPriority + 10
})

function openCreateRuleDialog() {
  editingRule.value = null
  showRuleDialog.value = true
}

function openEditRuleDialog(rule: AllocationRule) {
  editingRule.value = rule
  showRuleDialog.value = true
}

async function handleSaveRule(data: AllocationRuleFormData) {
  try {
    savingRule.value = true
    const payload = { ...data, envelope_id: envelopeId.value }

    if (editingRule.value) {
      await allocationRulesStore.updateAllocationRule(editingRule.value.id, payload)
    } else {
      await allocationRulesStore.createAllocationRule(payload)
    }
    showRuleDialog.value = false
  } catch {
    showSnackbar('Failed to save rule', 'error')
  } finally {
    savingRule.value = false
  }
}

function openDeleteRuleDialog(rule: AllocationRule) {
  deletingRuleId.value = rule.id
  showDeleteRuleDialog.value = true
}

async function handleDeleteRule() {
  if (!deletingRuleId.value) return

  try {
    deletingRule.value = true
    await allocationRulesStore.deleteAllocationRule(deletingRuleId.value)
    showDeleteRuleDialog.value = false
  } catch {
    showSnackbar('Failed to delete rule', 'error')
  } finally {
    deletingRule.value = false
  }
}

async function toggleRuleActive(rule: AllocationRule) {
  try {
    await allocationRulesStore.updateAllocationRule(rule.id, {
      is_active: !rule.is_active,
    })
  } catch {
    showSnackbar('Failed to update rule', 'error')
  }
}

</script>

<template>
  <div>
    <v-btn
      variant="text"
      to="/envelopes"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
    >
      Back to Envelopes
    </v-btn>

    <!-- Loading State -->
    <div
      v-if="loading && !envelope"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <template v-else-if="envelope">
      <!-- Header -->
      <div class="d-flex align-center mb-4">
        <v-avatar
          color="primary"
          variant="tonal"
          size="48"
          class="mr-3"
        >
          <!-- Show emoji if set (not an MDI icon), otherwise show MDI icon -->
          <span
            v-if="envelope.icon && !envelope.icon.startsWith('mdi-')"
            class="emoji-icon"
          >
            {{ envelope.icon }}
          </span>
          <v-icon
            v-else
            size="24"
          >
            {{ envelope.icon || 'mdi-wallet' }}
          </v-icon>
        </v-avatar>
        <div>
          <h1 class="text-h4">
            {{ envelope.name }}
          </h1>
          <span
            v-if="currentGroup"
            class="text-body-2 text-grey"
          >
            {{ currentGroup.name }}
          </span>
        </div>
        <v-spacer />
        <v-btn
          :icon="envelope.is_starred ? 'mdi-star' : 'mdi-star-outline'"
          :color="envelope.is_starred ? 'warning' : undefined"
          variant="text"
          :loading="starring"
          @click="handleToggleStar"
        />
        <v-btn
          icon="mdi-pencil"
          variant="text"
          @click="openEditDialog"
        />
      </div>

      <!-- Balance Card -->
      <v-card class="mb-4">
        <v-card-text>
          <div class="d-flex align-center justify-space-between mb-2">
            <span class="text-subtitle-2 text-medium-emphasis">Current Balance</span>
            <v-btn
              variant="tonal"
              size="small"
              prepend-icon="mdi-swap-horizontal"
              @click="openTransferDialog"
            >
              Transfer
            </v-btn>
          </div>

          <MoneyDisplay
            :amount="envelope.current_balance"
            class="text-h4 font-weight-bold"
            :class="{
              'text-error': envelope.current_balance < 0,
              'text-success': envelope.target_balance && envelope.current_balance >= envelope.target_balance,
            }"
          />

          <!-- Progress bar for target -->
          <template v-if="envelope.target_balance">
            <v-progress-linear
              :model-value="progressPercent ?? 0"
              :color="progressColor"
              height="8"
              rounded
              class="mt-4 mb-2"
            />
            <div class="d-flex justify-space-between text-body-2 text-medium-emphasis">
              <span>
                {{ progressPercent?.toFixed(0) }}% of goal
              </span>
              <span>
                Target: <MoneyDisplay :amount="envelope.target_balance" />
              </span>
            </div>
          </template>

          <p
            v-if="envelope.description"
            class="text-body-2 text-medium-emphasis mt-4"
          >
            {{ envelope.description }}
          </p>
        </v-card-text>
      </v-card>

      <!-- Allocation Rules -->
      <v-card class="mb-4">
        <v-card-title class="d-flex align-center">
          Allocation Rules
          <v-spacer />
          <v-btn
            size="small"
            variant="tonal"
            prepend-icon="mdi-plus"
            @click="openCreateRuleDialog"
          >
            Add Rule
          </v-btn>
        </v-card-title>

        <v-card-text
          v-if="envelopeRules.length === 0"
          class="text-center text-grey py-6"
        >
          <v-icon
            size="48"
            color="grey-lighten-1"
          >
            mdi-tune-vertical
          </v-icon>
          <p class="mt-2">
            No allocation rules for this envelope.
          </p>
          <p class="text-body-2">
            Rules automatically distribute income to your envelopes.
          </p>
        </v-card-text>

        <v-list v-else>
          <v-list-item
            v-for="rule in envelopeRules"
            :key="rule.id"
            :class="{ 'opacity-50': !rule.is_active }"
          >
            <template #prepend>
              <v-avatar
                color="primary"
                variant="tonal"
                size="40"
              >
                <v-icon>{{ getRuleTypeIcon(rule.rule_type) }}</v-icon>
              </v-avatar>
            </template>

            <v-list-item-title class="font-weight-medium">
              {{ rule.name || getRuleTypeLabel(rule.rule_type) }}
              <v-chip
                v-if="!rule.is_active"
                size="x-small"
                color="grey"
                class="ml-2"
              >
                Inactive
              </v-chip>
            </v-list-item-title>

            <v-list-item-subtitle>
              <span>{{ getRuleTypeLabel(rule.rule_type) }}</span>
              <span class="mx-1">·</span>
              <span>{{ formatRuleAmount(rule) }}</span>
              <span class="mx-1">·</span>
              <span>Priority: {{ rule.priority }}</span>
            </v-list-item-subtitle>

            <template #append>
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
                  <v-list-item @click="openEditRuleDialog(rule)">
                    <v-list-item-title>Edit</v-list-item-title>
                  </v-list-item>
                  <v-list-item @click="toggleRuleActive(rule)">
                    <v-list-item-title>
                      {{ rule.is_active ? 'Deactivate' : 'Activate' }}
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item
                    class="text-error"
                    @click="openDeleteRuleDialog(rule)"
                  >
                    <v-list-item-title>Delete</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </template>
          </v-list-item>
        </v-list>

        <v-card-actions v-if="envelopeRules.length > 0">
          <v-btn
            variant="text"
            size="small"
            to="/allocation-rules"
          >
            Manage All Rules
          </v-btn>
        </v-card-actions>
      </v-card>

      <!-- Recent Activity -->
      <v-card>
        <v-card-title class="d-flex align-center">
          Recent Activity
          <v-spacer />
          <v-chip size="small">
            {{ allocations.length }} allocations
          </v-chip>
        </v-card-title>

        <v-card-text
          v-if="allocations.length === 0"
          class="text-center text-grey py-8"
        >
          <v-icon
            size="48"
            color="grey-lighten-1"
          >
            mdi-history
          </v-icon>
          <p class="mt-2">
            No allocation history yet.
          </p>
        </v-card-text>

        <v-list v-else>
          <v-list-item
            v-for="allocation in allocations.slice(0, 20)"
            :key="allocation.id"
          >
            <template #prepend>
              <v-avatar
                :color="allocation.amount > 0 ? 'success' : 'error'"
                variant="tonal"
                size="40"
              >
                <v-icon>
                  {{ allocation.amount > 0 ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
                </v-icon>
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ allocation.memo || (allocation.amount > 0 ? 'Money added' : 'Money removed') }}
            </v-list-item-title>

            <v-list-item-subtitle>
              {{ formatAllocationDate(allocation) }}
            </v-list-item-subtitle>

            <template #append>
              <MoneyDisplay
                :amount="allocation.amount"
                class="font-weight-medium"
              />
            </template>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Delete Button -->
      <div class="mt-6 text-center">
        <v-btn
          color="error"
          variant="text"
          @click="showDeleteDialog = true"
        >
          Delete Envelope
        </v-btn>
      </div>
    </template>

    <!-- Edit Dialog -->
    <v-dialog
      v-model="showEditDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>Edit Envelope</v-card-title>
        <v-card-text>
          <div class="form-fields">
            <v-text-field
              v-model="editName"
              label="Name"
            />

            <v-text-field
              v-model="editIcon"
              label="Icon (emoji)"
              placeholder="🛒"
              hint="Optional - tap to open emoji keyboard"
              persistent-hint
              style="max-width: 120px"
            />

            <v-select
              v-model="editGroupId"
              label="Group"
              :items="groupOptions"
              clearable
            />

            <v-text-field
              v-model="editTargetBalance"
              label="Target Balance (optional)"
              type="number"
              step="0.01"
              min="0"
              prefix="$"
              hint="Set a savings goal for this envelope"
              persistent-hint
            />

            <v-textarea
              v-model="editDescription"
              label="Description (optional)"
              rows="2"
            />
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showEditDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="saving"
            :disabled="!editName.trim()"
            @click="handleSave"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Transfer Dialog -->
    <v-dialog
      v-model="showTransferDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Transfer Money</v-card-title>
        <v-card-text>
          <!-- Direction Toggle -->
          <v-btn-toggle
            v-model="transferDirection"
            mandatory
            density="compact"
            class="mb-4 d-flex"
          >
            <v-btn
              value="to"
              class="flex-grow-1"
            >
              To {{ envelope?.name }}
            </v-btn>
            <v-btn
              value="from"
              class="flex-grow-1"
            >
              From {{ envelope?.name }}
            </v-btn>
          </v-btn-toggle>

          <div class="form-fields">
            <v-select
              v-model="transferOtherId"
              :label="transferDirection === 'to' ? 'From Envelope' : 'To Envelope'"
              :items="transferableEnvelopes"
            />

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
            :disabled="!transferOtherId || !transferAmount || parseFloat(transferAmount) <= 0"
            @click="handleTransfer"
          >
            Transfer
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Delete Envelope</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ envelope?.name }}</strong>?
          <br><br>
          <v-alert
            v-if="envelope && envelope.current_balance !== 0"
            type="warning"
            variant="tonal"
            density="compact"
          >
            This envelope has a balance of
            <MoneyDisplay :amount="envelope.current_balance" />.
            The balance will be moved to Unallocated.
          </v-alert>
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

    <!-- Allocation Rule Dialog -->
    <v-dialog
      v-model="showRuleDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>
          {{ editingRule ? 'Edit Allocation Rule' : 'New Allocation Rule' }}
        </v-card-title>
        <v-card-text>
          <AllocationRuleForm
            :rule="editingRule"
            :envelope-id="envelopeId"
            :show-envelope-select="false"
            :loading="savingRule"
            :default-priority="nextRulePriority"
            :has-period-cap="hasPeriodCap"
            @submit="handleSaveRule"
            @cancel="showRuleDialog = false"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Delete Rule Dialog -->
    <v-dialog
      v-model="showDeleteRuleDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Delete Allocation Rule</v-card-title>
        <v-card-text>
          Are you sure you want to delete this allocation rule? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDeleteRuleDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deletingRule"
            @click="handleDeleteRule"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.emoji-icon {
  font-size: 24px;
  line-height: 1;
}
</style>
