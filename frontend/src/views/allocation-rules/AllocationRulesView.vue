<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import { useEnvelopesStore } from '@/stores/envelopes'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import AllocationRuleForm from '@/components/allocation-rules/AllocationRuleForm.vue'
import type { AllocationRuleFormData } from '@/components/allocation-rules/AllocationRuleForm.vue'
import type { AllocationRule, AllocationRuleType } from '@/types'
import type { RulePreviewResponse } from '@/api/allocationRules'

const allocationRulesStore = useAllocationRulesStore()
const envelopesStore = useEnvelopesStore()

// Filter state
const showInactive = ref(false)
const filterEnvelopeId = ref<string | null>(null)

// Form dialog state
const showFormDialog = ref(false)
const editingRule = ref<AllocationRule | null>(null)
const formLoading = ref(false)
const formEnvelopeId = ref<string | null>(null)

// Delete dialog
const showDeleteDialog = ref(false)
const deletingId = ref<string | null>(null)
const deleting = ref(false)

// Preview state
const showPreview = ref(false)
const previewAmount = ref('')
const previewLoading = ref(false)
const previewResult = ref<RulePreviewResponse | null>(null)

onMounted(async () => {
  try {
    await Promise.all([
      allocationRulesStore.fetchAllocationRules(),
      envelopesStore.fetchEnvelopes(),
    ])
  } catch {
    showSnackbar('Failed to load allocation rules', 'error')
  }
})

const displayedRules = computed(() => {
  let rules = showInactive.value
    ? allocationRulesStore.sortedRules
    : allocationRulesStore.activeRules

  if (filterEnvelopeId.value) {
    rules = rules.filter((r) => r.envelope_id === filterEnvelopeId.value)
  }

  return rules
})

type SelectOption = { title: string; value: string | null } | { type: 'subheader'; title: string }

const filterEnvelopeOptions = computed((): SelectOption[] => {
  const options: SelectOption[] = [{ title: 'All Envelopes', value: null }]

  // Get sorted groups
  const sortedGroups = envelopesStore.getSortedGroups()

  // Add envelopes grouped by their groups
  for (const group of sortedGroups) {
    const envelopesInGroup = envelopesStore.getEnvelopesInGroup(group.id)

    if (envelopesInGroup.length > 0) {
      options.push({ type: 'subheader', title: group.name })
      for (const envelope of envelopesInGroup) {
        options.push({ title: envelope.name, value: envelope.id })
      }
    }
  }

  // Add ungrouped envelopes at the end
  const ungroupedEnvelopes = envelopesStore.getEnvelopesInGroup(null)

  if (ungroupedEnvelopes.length > 0) {
    options.push({ type: 'subheader', title: 'Other' })
    for (const envelope of ungroupedEnvelopes) {
      options.push({ title: envelope.name, value: envelope.id })
    }
  }

  return options
})

const formHasPeriodCap = computed(() => {
  const envId = formEnvelopeId.value || editingRule.value?.envelope_id
  if (!envId) return false
  return allocationRulesStore.envelopeHasPeriodCap(envId, editingRule.value?.id)
})

const nextPriority = computed(() => {
  const rules = allocationRulesStore.sortedRules
  if (rules.length === 0) return 10
  const maxPriority = Math.max(...rules.map((r) => r.priority))
  return maxPriority + 10
})

function getEnvelopeName(id: string): string {
  return envelopesStore.getEnvelopeById(id)?.name || 'Unknown'
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

function openCreateDialog() {
  editingRule.value = null
  formEnvelopeId.value = null
  showFormDialog.value = true
}

function openEditDialog(rule: AllocationRule) {
  editingRule.value = rule
  formEnvelopeId.value = rule.envelope_id
  showFormDialog.value = true
}

async function handleFormSubmit(data: AllocationRuleFormData) {
  try {
    formLoading.value = true

    if (editingRule.value) {
      await allocationRulesStore.updateAllocationRule(editingRule.value.id, data)
    } else {
      await allocationRulesStore.createAllocationRule(data)
    }

    showFormDialog.value = false
  } catch {
    showSnackbar('Failed to save rule', 'error')
  } finally {
    formLoading.value = false
  }
}

function openDeleteDialog(rule: AllocationRule) {
  deletingId.value = rule.id
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deletingId.value) return

  try {
    deleting.value = true
    await allocationRulesStore.deleteAllocationRule(deletingId.value)
    showDeleteDialog.value = false
  } catch {
    showSnackbar('Failed to delete rule', 'error')
  } finally {
    deleting.value = false
  }
}

async function toggleActive(rule: AllocationRule) {
  try {
    await allocationRulesStore.updateAllocationRule(rule.id, {
      is_active: !rule.is_active,
    })
  } catch {
    showSnackbar('Failed to update rule', 'error')
  }
}

async function movePriority(rule: AllocationRule, direction: 'up' | 'down') {
  const currentIndex = displayedRules.value.findIndex((r) => r.id === rule.id)
  const swapIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

  if (swapIndex < 0 || swapIndex >= displayedRules.value.length) return

  const otherRule = displayedRules.value[swapIndex]
  if (!otherRule) return

  // Swap priorities
  const newPriority = otherRule.priority
  const otherNewPriority = rule.priority

  try {
    await Promise.all([
      allocationRulesStore.updateAllocationRule(rule.id, { priority: newPriority }),
      allocationRulesStore.updateAllocationRule(otherRule.id, { priority: otherNewPriority }),
    ])
  } catch {
    showSnackbar('Failed to update priority', 'error')
  }
}

async function runPreview() {
  const amount = parseFloat(previewAmount.value)
  if (!amount || amount <= 0) {
    showSnackbar('Please enter a valid amount', 'error')
    return
  }

  try {
    previewLoading.value = true
    previewResult.value = await allocationRulesStore.previewRules(Math.round(amount * 100))
  } catch {
    showSnackbar('Failed to preview allocation', 'error')
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">
        Allocation Rules
      </h1>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Add Rule
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
              Active Rules
            </div>
            <div class="text-h6">
              {{ allocationRulesStore.activeRules.length }}
            </div>
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
              Total Rules
            </div>
            <div class="text-h6">
              {{ allocationRulesStore.allocationRules.length }}
            </div>
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
              Envelopes Covered
            </div>
            <div class="text-h6">
              {{ Object.keys(allocationRulesStore.rulesByEnvelope).length }}
            </div>
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
              Remainder Rules
            </div>
            <div class="text-h6">
              {{ allocationRulesStore.activeRules.filter((r) => r.rule_type === 'remainder').length }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Preview Section -->
    <v-expansion-panels
      v-model="showPreview"
      class="mb-4"
    >
      <v-expansion-panel value="preview">
        <v-expansion-panel-title>
          <v-icon class="mr-2">
            mdi-eye
          </v-icon>
          Preview Income Distribution
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div class="d-flex gap-2 mb-4">
            <v-text-field
              v-model="previewAmount"
              label="Income Amount"
              type="number"
              step="0.01"
              min="0"
              prefix="$"
              hide-details
              style="max-width: 200px"
            />
            <v-btn
              color="primary"
              :loading="previewLoading"
              :disabled="!previewAmount"
              @click="runPreview"
            >
              Preview
            </v-btn>
          </div>

          <v-table
            v-if="previewResult"
            density="compact"
          >
            <thead>
              <tr>
                <th>Rule</th>
                <th>Envelope</th>
                <th class="text-right">
                  Amount
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="alloc in previewResult.allocations"
                :key="alloc.rule_id"
              >
                <td>{{ alloc.rule_name || 'Unnamed Rule' }}</td>
                <td>{{ getEnvelopeName(alloc.envelope_id) }}</td>
                <td class="text-right">
                  <MoneyDisplay :amount="alloc.amount" />
                </td>
              </tr>
              <tr v-if="previewResult.unallocated > 0">
                <td
                  colspan="2"
                  class="text-medium-emphasis"
                >
                  Unallocated
                </td>
                <td class="text-right text-medium-emphasis">
                  <MoneyDisplay :amount="previewResult.unallocated" />
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="font-weight-bold">
                <td colspan="2">
                  Total
                </td>
                <td class="text-right">
                  <MoneyDisplay :amount="previewResult.income_amount" />
                </td>
              </tr>
            </tfoot>
          </v-table>

          <div
            v-else-if="allocationRulesStore.activeRules.length === 0"
            class="text-medium-emphasis"
          >
            Create some rules first to see a preview.
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col
            cols="12"
            sm="6"
            md="4"
          >
            <v-select
              v-model="filterEnvelopeId"
              label="Filter by Envelope"
              :items="filterEnvelopeOptions"
              hide-details
              density="compact"
            />
          </v-col>
          <v-col
            cols="12"
            sm="6"
            md="4"
          >
            <v-switch
              v-model="showInactive"
              label="Show inactive"
              hide-details
              density="compact"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Loading State -->
    <div
      v-if="allocationRulesStore.loading && allocationRulesStore.allocationRules.length === 0"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <!-- Empty State -->
    <v-card v-else-if="displayedRules.length === 0">
      <v-card-text class="text-center text-grey py-8">
        <v-icon
          size="64"
          color="grey-lighten-1"
        >
          mdi-tune-vertical
        </v-icon>
        <p class="mt-4">
          {{ filterEnvelopeId || !showInactive ? 'No rules match your filters.' : 'No allocation rules yet.' }}
        </p>
        <p class="text-body-2">
          Allocation rules automatically distribute income to your envelopes.
        </p>
        <v-btn
          color="primary"
          class="mt-4"
          @click="openCreateDialog"
        >
          Create Your First Rule
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- Rules List -->
    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="(rule, index) in displayedRules"
          :key="rule.id"
          :class="{ 'opacity-50': !rule.is_active }"
        >
          <template #prepend>
            <div class="d-flex flex-column align-center mr-2">
              <v-btn
                icon="mdi-chevron-up"
                size="x-small"
                variant="text"
                :disabled="index === 0"
                @click="movePriority(rule, 'up')"
              />
              <v-chip
                size="small"
                color="primary"
                variant="tonal"
              >
                {{ rule.priority }}
              </v-chip>
              <v-btn
                icon="mdi-chevron-down"
                size="x-small"
                variant="text"
                :disabled="index === displayedRules.length - 1"
                @click="movePriority(rule, 'down')"
              />
            </div>
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
            <span>{{ getEnvelopeName(rule.envelope_id) }}</span>
            <span class="mx-1">·</span>
            <span>{{ getRuleTypeLabel(rule.rule_type) }}</span>
            <span class="mx-1">·</span>
            <span>{{ formatRuleAmount(rule) }}</span>
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
                <v-list-item @click="openEditDialog(rule)">
                  <v-list-item-title>Edit</v-list-item-title>
                </v-list-item>
                <v-list-item @click="toggleActive(rule)">
                  <v-list-item-title>
                    {{ rule.is_active ? 'Deactivate' : 'Activate' }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item
                  class="text-error"
                  @click="openDeleteDialog(rule)"
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
          {{ editingRule ? 'Edit Allocation Rule' : 'New Allocation Rule' }}
        </v-card-title>
        <v-card-text>
          <AllocationRuleForm
            :rule="editingRule"
            :loading="formLoading"
            :default-priority="nextPriority"
            :has-period-cap="formHasPeriodCap"
            @submit="handleFormSubmit"
            @cancel="showFormDialog = false"
            @update:envelope-id="formEnvelopeId = $event"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Delete Allocation Rule</v-card-title>
        <v-card-text>
          Are you sure you want to delete this allocation rule? This action cannot be undone.
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
