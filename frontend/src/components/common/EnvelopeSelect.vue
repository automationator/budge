<script setup lang="ts">
import { computed, ref } from 'vue'
import { useEnvelopesStore } from '@/stores/envelopes'
import { formatMoney } from '@/utils/money'

type SelectOption = { title: string; value: string } | { type: 'subheader'; title: string }

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    label?: string
    hint?: string
    persistentHint?: boolean
    clearable?: boolean
    disabled?: boolean
    grouped?: boolean
    showBalances?: boolean
    excludeIds?: string[]
    includeUnallocated?: boolean
    includeCreditCards?: boolean
    density?: 'default' | 'comfortable' | 'compact'
    hideDetails?: boolean | 'auto'
    rules?: ((v: unknown) => boolean | string)[]
  }>(),
  {
    label: 'Envelope',
    hint: undefined,
    persistentHint: false,
    clearable: false,
    disabled: false,
    grouped: true,
    showBalances: false,
    excludeIds: () => [],
    includeUnallocated: true,
    includeCreditCards: false,
    density: 'default',
    hideDetails: false,
    rules: () => [],
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const envelopesStore = useEnvelopesStore()

// Search state
const envelopeSearch = ref('')

const selectedValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const formatLabel = (name: string, balance: number): string => {
  if (props.showBalances) {
    return `${name} (${formatMoney(balance)})`
  }
  return name
}

const envelopeOptions = computed((): SelectOption[] => {
  const options: SelectOption[] = []
  const excludeSet = new Set(props.excludeIds)

  // Add Unallocated first if included
  if (props.includeUnallocated) {
    const unallocated = envelopesStore.envelopes.find((e) => e.is_unallocated)
    if (unallocated && !excludeSet.has(unallocated.id)) {
      options.push({
        title: formatLabel(unallocated.name, unallocated.current_balance),
        value: unallocated.id,
      })
    }
  }

  if (props.grouped) {
    // Get sorted groups
    const sortedGroups = envelopesStore.getSortedGroups()

    // Add envelopes grouped by their groups
    for (const group of sortedGroups) {
      const envelopesInGroup = envelopesStore
        .getEnvelopesInGroup(group.id)
        .filter((e) => !excludeSet.has(e.id))

      if (envelopesInGroup.length > 0) {
        options.push({ type: 'subheader', title: group.name })
        for (const envelope of envelopesInGroup) {
          options.push({
            title: formatLabel(envelope.name, envelope.current_balance),
            value: envelope.id,
          })
        }
      }
    }

    // Add ungrouped envelopes at the end
    const ungroupedEnvelopes = envelopesStore
      .getEnvelopesInGroup(null)
      .filter((e) => !excludeSet.has(e.id))

    if (ungroupedEnvelopes.length > 0) {
      options.push({ type: 'subheader', title: 'Other' })
      for (const envelope of ungroupedEnvelopes) {
        options.push({
          title: formatLabel(envelope.name, envelope.current_balance),
          value: envelope.id,
        })
      }
    }

    // Add credit card envelopes at the bottom (if enabled)
    if (props.includeCreditCards) {
      const ccEnvelopes = envelopesStore.creditCardEnvelopes.filter(
        (e) => !excludeSet.has(e.id)
      )

      if (ccEnvelopes.length > 0) {
        options.push({ type: 'subheader', title: 'Credit Cards' })
        for (const envelope of ccEnvelopes) {
          options.push({
            title: formatLabel(envelope.name, envelope.current_balance),
            value: envelope.id,
          })
        }
      }
    }
  } else {
    // Flat list without grouping
    const activeEnvelopes = envelopesStore.activeEnvelopes.filter(
      (e) => !excludeSet.has(e.id) && !e.is_unallocated
    )
    for (const envelope of activeEnvelopes) {
      options.push({
        title: formatLabel(envelope.name, envelope.current_balance),
        value: envelope.id,
      })
    }
  }

  return options
})

// Add fallback for unknown envelope IDs (deleted or not loaded yet)
// This prevents showing raw UUIDs in the select
const optionsWithFallback = computed((): SelectOption[] => {
  if (!props.modelValue) return envelopeOptions.value

  // Check if the current value exists in options
  const valueExists = envelopeOptions.value.some(
    (opt) => 'value' in opt && opt.value === props.modelValue
  )

  if (valueExists) return envelopeOptions.value

  // Add a placeholder option for the unknown envelope
  return [
    { title: 'Unknown Envelope', value: props.modelValue },
    ...envelopeOptions.value,
  ]
})

const filteredOptions = computed((): SelectOption[] => {
  if (!envelopeSearch.value) return optionsWithFallback.value

  const search = envelopeSearch.value.toLowerCase()
  const result: SelectOption[] = []
  let currentSubheader: SelectOption | null = null
  let childrenForCurrentSubheader: SelectOption[] = []

  for (const opt of optionsWithFallback.value) {
    if ('type' in opt && opt.type === 'subheader') {
      // Flush previous group if it had matching children
      if (currentSubheader && childrenForCurrentSubheader.length > 0) {
        result.push(currentSubheader, ...childrenForCurrentSubheader)
      }
      currentSubheader = opt
      childrenForCurrentSubheader = []
    } else if (currentSubheader) {
      // Child of a group
      if (opt.title.toLowerCase().includes(search)) {
        childrenForCurrentSubheader.push(opt)
      }
    } else {
      // Top-level item (e.g. Unallocated, or flat list)
      if (opt.title.toLowerCase().includes(search)) {
        result.push(opt)
      }
    }
  }

  // Flush last group
  if (currentSubheader && childrenForCurrentSubheader.length > 0) {
    result.push(currentSubheader, ...childrenForCurrentSubheader)
  }

  return result
})
</script>

<template>
  <v-autocomplete
    v-model="selectedValue"
    v-model:search="envelopeSearch"
    :label="label"
    :items="filteredOptions"
    :hint="hint"
    :persistent-hint="persistentHint"
    :clearable="clearable"
    :disabled="disabled"
    :density="density"
    :hide-details="hideDetails"
    :rules="rules"
    auto-select-first
    no-filter
  />
</template>
