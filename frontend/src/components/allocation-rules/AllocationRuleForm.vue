<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { AllocationRule, AllocationRuleType } from '@/types'
import { useEnvelopesStore } from '@/stores/envelopes'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'

export interface AllocationRuleFormData {
  envelope_id: string
  rule_type: AllocationRuleType
  amount: number
  priority: number
  is_active: boolean
  name: string | null
  respect_target: boolean
  cap_period_value?: number
  cap_period_unit?: string | null
}

interface Props {
  /** Existing rule for edit mode */
  rule?: AllocationRule | null
  /** Pre-selected envelope ID (hides envelope selector when provided) */
  envelopeId?: string | null
  /** Loading state for submit button */
  loading?: boolean
  /** Show the envelope dropdown */
  showEnvelopeSelect?: boolean
  /** Default priority for new rules */
  defaultPriority?: number
  /** Restrict available rule types */
  allowedRuleTypes?: AllocationRuleType[]
  /** Show submit/cancel buttons */
  showActions?: boolean
  /** Default name for the rule (e.g., envelope name) */
  defaultName?: string | null
  /** Whether the target envelope already has a period_cap rule */
  hasPeriodCap?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  rule: null,
  envelopeId: null,
  loading: false,
  showEnvelopeSelect: true,
  defaultPriority: 0,
  allowedRuleTypes: () => ['fill_to_target', 'fixed', 'percentage', 'remainder', 'period_cap'],
  showActions: true,
  defaultName: null,
  hasPeriodCap: false,
})

const envelopesStore = useEnvelopesStore()

const emit = defineEmits<{
  submit: [data: AllocationRuleFormData]
  cancel: []
  'update:valid': [isValid: boolean]
  'update:ruleType': [ruleType: AllocationRuleType]
  'update:envelopeId': [envelopeId: string | null]
}>()

// Form state
const formName = ref('')
const formEnvelopeId = ref<string | null>(null)
const formRuleType = ref<AllocationRuleType>('fixed')
const formAmount = ref('')
const formPriority = ref('0')
const formIsActive = ref(true)
const formRespectTarget = ref(true)
const formCapPeriodValue = ref('1')
const formCapPeriodUnit = ref<string | null>(null)

// Rule type options
const allRuleTypeOptions = [
  { title: 'Fill to Target', value: 'fill_to_target' as AllocationRuleType },
  { title: 'Fixed Amount', value: 'fixed' as AllocationRuleType },
  { title: 'Percentage', value: 'percentage' as AllocationRuleType },
  { title: 'Remainder', value: 'remainder' as AllocationRuleType },
  { title: 'Period Cap', value: 'period_cap' as AllocationRuleType },
]

const filteredRuleTypeOptions = computed(() =>
  allRuleTypeOptions.filter((opt) => {
    if (!props.allowedRuleTypes.includes(opt.value)) return false
    if (opt.value === 'period_cap' && props.hasPeriodCap) return false
    return true
  })
)

const isEditing = computed(() => !!props.rule)

// Helper functions
function getRuleTypeHint(type: AllocationRuleType): string {
  switch (type) {
    case 'fill_to_target':
      return "Allocates up to the envelope's target balance"
    case 'fixed':
      return 'Allocates a specific dollar amount each time'
    case 'percentage':
      return 'Allocates a percentage of remaining income'
    case 'remainder':
      return 'Splits leftover income by weight with other remainder rules'
    case 'period_cap':
      return 'Limits how much income can be allocated to this envelope per time period'
  }
}

function getAmountLabel(): string {
  switch (formRuleType.value) {
    case 'fixed':
      return 'Amount ($)'
    case 'percentage':
      return 'Percentage (%)'
    case 'remainder':
      return 'Weight'
    case 'period_cap':
      return 'Cap Amount ($)'
    default:
      return 'Amount'
  }
}

function getAmountHint(): string {
  switch (formRuleType.value) {
    case 'fixed':
      return 'Dollar amount to allocate'
    case 'percentage':
      return 'Percentage of remaining income (e.g., 10 for 10%)'
    case 'remainder':
      return 'Relative weight for splitting remainder with other rules'
    case 'period_cap':
      return 'Maximum dollar amount to allocate per time period'
    default:
      return ''
  }
}

function getAmountForStorage(): number {
  const value = parseFloat(formAmount.value) || 0
  switch (formRuleType.value) {
    case 'fill_to_target':
      return 0
    case 'fixed':
      return Math.round(value * 100) // dollars to cents
    case 'percentage':
      return Math.round(value * 100) // percent to basis points
    case 'remainder':
      return Math.round(value) // weight as-is
    case 'period_cap':
      return Math.round(value * 100) // dollars to cents
  }
}

function setAmountFromRule(rule: AllocationRule) {
  switch (rule.rule_type) {
    case 'fill_to_target':
      formAmount.value = ''
      break
    case 'fixed':
      formAmount.value = (rule.amount / 100).toFixed(2)
      break
    case 'percentage':
      formAmount.value = (rule.amount / 100).toFixed(1)
      break
    case 'remainder':
      formAmount.value = rule.amount.toString()
      break
    case 'period_cap':
      formAmount.value = (rule.amount / 100).toFixed(2)
      break
  }
}

function populateFromRule(rule: AllocationRule) {
  formName.value = rule.name || ''
  formEnvelopeId.value = rule.envelope_id
  formRuleType.value = rule.rule_type
  setAmountFromRule(rule)
  formPriority.value = rule.priority.toString()
  formIsActive.value = rule.is_active
  formRespectTarget.value = rule.respect_target
  formCapPeriodValue.value = rule.cap_period_value?.toString() || '1'
  formCapPeriodUnit.value = rule.cap_period_unit || null
}

function resetForm() {
  formName.value = props.defaultName || ''
  formEnvelopeId.value = props.envelopeId || null
  formRuleType.value = props.allowedRuleTypes.includes('fixed') ? 'fixed' : (props.allowedRuleTypes[0] ?? 'fixed')
  formAmount.value = ''
  formPriority.value = props.defaultPriority.toString()
  formIsActive.value = true
  formRespectTarget.value = true
  formCapPeriodValue.value = '1'
  formCapPeriodUnit.value = null
}

// Watch for rule prop changes (edit mode)
watch(
  () => props.rule,
  (newRule) => {
    if (newRule) {
      populateFromRule(newRule)
    } else {
      resetForm()
    }
  },
  { immediate: true }
)

// Watch for envelopeId prop changes
watch(
  () => props.envelopeId,
  (newId) => {
    if (newId) {
      formEnvelopeId.value = newId
    }
  },
  { immediate: true }
)

// Watch for defaultPriority prop changes
watch(
  () => props.defaultPriority,
  (newPriority) => {
    if (!props.rule) {
      formPriority.value = newPriority.toString()
    }
  },
  { immediate: true }
)

// Watch for defaultName prop changes (real-time sync with envelope name)
watch(
  () => props.defaultName,
  (newName) => {
    if (!props.rule && newName !== null) {
      formName.value = newName
    }
  }
)

// Auto-set name from envelope selection (when using dropdown)
watch(formEnvelopeId, (newId) => {
  emit('update:envelopeId', newId)

  // Only auto-set if not editing, showing envelope select, and name is empty
  if (!props.rule && props.showEnvelopeSelect && newId && !formName.value.trim()) {
    const selectedEnvelope = envelopesStore.getEnvelopeById(newId)
    if (selectedEnvelope) {
      formName.value = selectedEnvelope.name
    }
  }
})

// Validation
const isFormValid = computed((): boolean => {
  const hasEnvelope = !!(props.envelopeId || formEnvelopeId.value || !props.showEnvelopeSelect)
  const hasAmount =
    formRuleType.value === 'fill_to_target' || (parseFloat(formAmount.value) || 0) > 0
  if (formRuleType.value === 'period_cap') {
    return hasEnvelope && hasAmount && !!formCapPeriodUnit.value
  }
  return hasEnvelope && hasAmount
})

// Emit validity changes - use onMounted for initial emit to ensure parent's event handler is attached
watch(isFormValid, (valid: boolean) => emit('update:valid', valid))

// Emit rule type changes
watch(formRuleType, (ruleType: AllocationRuleType) => emit('update:ruleType', ruleType))

onMounted(() => {
  emit('update:valid', isFormValid.value as boolean)
  emit('update:ruleType', formRuleType.value as AllocationRuleType)
})

// Get form data for submission
function getFormData(): AllocationRuleFormData | null {
  if (!isFormValid.value) return null

  const envelopeId = props.envelopeId || formEnvelopeId.value
  if (!envelopeId && props.showEnvelopeSelect) return null

  const data: AllocationRuleFormData = {
    envelope_id: envelopeId || '',
    rule_type: formRuleType.value,
    amount: getAmountForStorage(),
    priority: formRuleType.value === 'period_cap' ? 0 : (parseInt(formPriority.value) || 0),
    is_active: formIsActive.value,
    name: formName.value.trim() || null,
    respect_target: formRespectTarget.value,
  }

  if (formRuleType.value === 'period_cap') {
    data.cap_period_value = parseInt(formCapPeriodValue.value) || 1
    data.cap_period_unit = formCapPeriodUnit.value
  }

  return data
}

function handleSubmit() {
  const data = getFormData()
  if (data) emit('submit', data)
}

// Expose methods for parent components
defineExpose({
  getFormData,
  isValid: () => isFormValid.value,
  reset: resetForm,
  formRuleType,
})
</script>

<template>
  <v-form @submit.prevent="handleSubmit">
    <!-- Name -->
    <v-text-field
      v-model="formName"
      label="Name (optional)"
      hint="Give this rule a descriptive name"
      persistent-hint
      class="mb-4"
    />

    <!-- Envelope -->
    <EnvelopeSelect
      v-if="showEnvelopeSelect && !envelopeId"
      v-model="formEnvelopeId"
      label="Envelope"
      :include-unallocated="false"
      class="mb-4"
    />

    <!-- Rule Type -->
    <v-select
      v-model="formRuleType"
      label="Rule Type"
      :items="filteredRuleTypeOptions"
      :hint="getRuleTypeHint(formRuleType)"
      persistent-hint
      class="mb-4"
    />

    <!-- Amount (hidden for fill_to_target) -->
    <v-text-field
      v-if="formRuleType !== 'fill_to_target'"
      v-model="formAmount"
      :label="getAmountLabel()"
      type="number"
      step="0.01"
      min="0"
      :hint="getAmountHint()"
      persistent-hint
      class="mb-4"
    />

    <!-- Period Cap fields (only for period_cap rules) -->
    <v-row v-if="formRuleType === 'period_cap'">
      <v-col cols="6">
        <v-text-field
          v-model="formCapPeriodValue"
          label="Every"
          type="number"
          min="1"
          class="mb-4"
        />
      </v-col>
      <v-col cols="6">
        <v-select
          v-model="formCapPeriodUnit"
          label="Period"
          :items="[
            { title: 'Week(s)', value: 'week' },
            { title: 'Month(s)', value: 'month' },
            { title: 'Year(s)', value: 'year' },
          ]"
          class="mb-4"
        />
      </v-col>
    </v-row>

    <!-- Priority (hidden for period_cap) -->
    <v-text-field
      v-if="formRuleType !== 'period_cap'"
      v-model="formPriority"
      label="Priority"
      type="number"
      min="0"
      hint="Lower numbers execute first"
      persistent-hint
      class="mb-4"
    />

    <!-- Respect Target (not for fill_to_target or period_cap) -->
    <v-switch
      v-if="formRuleType !== 'fill_to_target' && formRuleType !== 'period_cap'"
      v-model="formRespectTarget"
      label="Stop at target balance"
      hint="Only allocate until envelope reaches its target balance"
      persistent-hint
      class="mb-4"
    />

    <!-- Active -->
    <v-switch
      v-model="formIsActive"
      label="Active"
      hint="Inactive rules are skipped during allocation"
      persistent-hint
      hide-details
    />

    <!-- Actions -->
    <div
      v-if="showActions"
      class="d-flex justify-end gap-2 mt-6"
    >
      <v-btn
        variant="text"
        @click="emit('cancel')"
      >
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        type="submit"
        :loading="loading"
        :disabled="!isFormValid"
      >
        {{ isEditing ? 'Save' : 'Create' }}
      </v-btn>
    </div>
  </v-form>
</template>
