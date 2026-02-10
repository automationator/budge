<script setup lang="ts">
import { computed } from 'vue'
import { useAccountsStore } from '@/stores/accounts'

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
    excludeIds?: string[]
    density?: 'default' | 'comfortable' | 'compact'
    hideDetails?: boolean | 'auto'
    rules?: ((v: unknown) => boolean | string)[]
  }>(),
  {
    label: 'Account',
    hint: undefined,
    persistentHint: false,
    clearable: false,
    disabled: false,
    grouped: true,
    excludeIds: () => [],
    density: 'default',
    hideDetails: false,
    rules: () => [],
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const accountsStore = useAccountsStore()

const selectedValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const accountOptions = computed((): SelectOption[] => {
  const options: SelectOption[] = []
  const excludeSet = new Set(props.excludeIds)

  const sortAccounts = (accounts: typeof accountsStore.activeAccounts) =>
    [...accounts].sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.name.localeCompare(b.name)
    })

  if (props.grouped) {
    const budgetAccounts = sortAccounts(
      accountsStore.activeAccounts.filter((a) => a.include_in_budget && !excludeSet.has(a.id))
    )
    const trackingAccounts = sortAccounts(
      accountsStore.activeAccounts.filter((a) => !a.include_in_budget && !excludeSet.has(a.id))
    )

    if (budgetAccounts.length > 0) {
      options.push({ type: 'subheader', title: 'Budget' })
      for (const account of budgetAccounts) {
        options.push({ title: account.name, value: account.id })
      }
    }

    if (trackingAccounts.length > 0) {
      options.push({ type: 'subheader', title: 'Tracking' })
      for (const account of trackingAccounts) {
        options.push({ title: account.name, value: account.id })
      }
    }
  } else {
    // Flat list without grouping
    const accounts = sortAccounts(
      accountsStore.activeAccounts.filter((a) => !excludeSet.has(a.id))
    )
    for (const account of accounts) {
      options.push({ title: account.name, value: account.id })
    }
  }

  return options
})
</script>

<template>
  <v-select
    v-model="selectedValue"
    :label="label"
    :items="accountOptions"
    :hint="hint"
    :persistent-hint="persistentHint"
    :clearable="clearable"
    :disabled="disabled"
    :density="density"
    :hide-details="hideDetails"
    :rules="rules"
  />
</template>
