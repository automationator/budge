<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    label?: string
    disabled?: boolean
    density?: 'default' | 'comfortable' | 'compact'
    hideDetails?: boolean | 'auto'
    rules?: ((v: unknown) => boolean | string)[]
    required?: boolean
    isExpense?: boolean | null
    autofocus?: boolean
  }>(),
  {
    label: 'Amount',
    disabled: false,
    density: 'default',
    hideDetails: false,
    rules: () => [],
    required: true,
    isExpense: null,
    autofocus: false,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:isExpense': [value: boolean]
}>()

// Internal raw digits (no decimal point)
const rawDigits = ref('')

// Track if we're in the middle of processing to avoid loops
const isProcessing = ref(false)

// Convert raw digits to formatted display value with auto-decimal
// e.g., "1234" → "12.34", "5" → "0.05"
const formattedValue = computed(() => {
  if (!rawDigits.value) return ''
  const padded = rawDigits.value.padStart(3, '0')
  const dollars = padded.slice(0, -2)
  const cents = padded.slice(-2)
  return `${parseInt(dollars, 10)}.${cents}`
})

// Sync from modelValue prop (on mount or external changes)
watch(
  () => props.modelValue,
  (newVal) => {
    if (isProcessing.value) return

    if (newVal) {
      // Convert "12.34" to "1234"
      const digits = newVal.replace(/\D/g, '')
      // Remove leading zeros but keep at least one digit if all zeros
      const trimmed = digits.replace(/^0+/, '')
      rawDigits.value = trimmed || (digits.length > 0 ? '0' : '')
    } else {
      rawDigits.value = ''
    }
  },
  { immediate: true }
)

// Handle model value updates from Vuetify - auto-format with decimal
function handleModelUpdate(value: string | null) {
  isProcessing.value = true

  const newDigits = (value || '').replace(/\D/g, '')

  // Remove leading zeros (but keep at least one digit if input has content)
  const trimmed = newDigits.replace(/^0+/, '')
  rawDigits.value = trimmed || (newDigits.length > 0 ? '0' : '')

  // Emit formatted value
  emit('update:modelValue', formattedValue.value)

  // Use nextTick to avoid immediate re-render issues
  nextTick(() => {
    isProcessing.value = false
  })
}

// Built-in validation rules
const positiveNumberRules = [
  (v: string) => !!v || 'Required',
  (v: string) => parseFloat(v) > 0 || 'Must be greater than 0',
]

const computedRules = computed(() => {
  if (props.rules.length > 0) {
    // Use custom rules if provided
    return props.rules
  }
  // Use built-in validation based on required prop
  return props.required ? positiveNumberRules : []
})

const showSignToggle = computed(() => props.isExpense !== null)

const toggleSign = () => {
  if (!props.disabled && props.isExpense !== null) {
    emit('update:isExpense', !props.isExpense)
  }
}
</script>

<template>
  <v-text-field
    :model-value="formattedValue"
    :label="label"
    type="text"
    inputmode="numeric"
    :prefix="showSignToggle ? undefined : '$'"
    :rules="computedRules"
    :disabled="disabled"
    :density="density"
    :hide-details="hideDetails"
    :autofocus="autofocus"
    @update:model-value="handleModelUpdate"
  >
    <template
      v-if="showSignToggle"
      #prepend-inner
    >
      <span
        class="sign-toggle"
        :class="{ expense: isExpense, income: !isExpense, disabled: disabled }"
        role="button"
        tabindex="0"
        data-testid="amount-sign-toggle"
        @click="toggleSign"
        @keydown.enter="toggleSign"
        @keydown.space.prevent="toggleSign"
      >
        {{ isExpense ? '−$' : '+$' }}
      </span>
    </template>
  </v-text-field>
</template>

<style scoped>
.sign-toggle {
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background-color 0.15s;
  white-space: nowrap;
}

.sign-toggle:hover:not(.disabled) {
  background-color: rgba(0, 0, 0, 0.08);
}

.sign-toggle.expense {
  color: rgb(var(--v-theme-error));
}

.sign-toggle.income {
  color: rgb(var(--v-theme-success));
}

.sign-toggle.disabled {
  cursor: default;
  opacity: 0.6;
}
</style>
