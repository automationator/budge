<script setup lang="ts">
import { computed, ref } from 'vue'
import { usePayeesStore } from '@/stores/payees'
import { showSnackbar } from '@/App.vue'

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    label?: string
    hint?: string
    persistentHint?: boolean
    clearable?: boolean
    disabled?: boolean
    density?: 'default' | 'comfortable' | 'compact'
    hideDetails?: boolean | 'auto'
    rules?: ((v: unknown) => boolean | string)[]
    allowCreate?: boolean
  }>(),
  {
    label: 'Payee',
    hint: undefined,
    persistentHint: false,
    clearable: false,
    disabled: false,
    density: 'default',
    hideDetails: false,
    rules: () => [],
    allowCreate: true,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const payeesStore = usePayeesStore()

// Search state
const payeeSearch = ref('')

function titleCase(str: string): string {
  return str.replace(/\S+/g, (word) => {
    if (word === word.toLowerCase()) {
      return word.charAt(0).toUpperCase() + word.slice(1)
    }
    return word
  })
}

// Create state
const creating = ref(false)

// Autocomplete ref for closing menu
const autocompleteRef = ref<{ blur: () => void } | null>(null)

const selectedValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const payeeOptions = computed(() =>
  payeesStore.sortedPayees.map((p) => ({ title: p.name, value: p.id }))
)

const filteredPayeeOptions = computed(() => {
  if (!payeeSearch.value) return payeeOptions.value
  const search = payeeSearch.value.toLowerCase()
  return payeeOptions.value.filter((p) => p.title.toLowerCase().includes(search))
})

const showCreatePayeeOption = computed(() => {
  if (!props.allowCreate || !payeeSearch.value || creating.value) return false
  const search = payeeSearch.value.toLowerCase()
  return !payeeOptions.value.some((p) => p.title.toLowerCase() === search)
})

async function createNewPayee() {
  if (!payeeSearch.value.trim() || creating.value) return

  try {
    creating.value = true
    const payee = await payeesStore.createPayee({ name: titleCase(payeeSearch.value.trim()) })
    selectedValue.value = payee.id
    payeeSearch.value = ''
    // Close the dropdown menu
    autocompleteRef.value?.blur()
  } catch {
    showSnackbar('Failed to create payee', 'error')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <v-autocomplete
    ref="autocompleteRef"
    v-model="selectedValue"
    v-model:search="payeeSearch"
    :label="label"
    :items="filteredPayeeOptions"
    :hint="hint"
    :persistent-hint="persistentHint"
    :clearable="clearable"
    :disabled="disabled"
    :density="density"
    :hide-details="hideDetails"
    :rules="rules"
    autocapitalize="words"
    auto-select-first
  >
    <template #no-data>
      <v-list-item
        v-if="showCreatePayeeOption"
        @click="createNewPayee"
      >
        <v-list-item-title>
          <v-icon
            start
            size="small"
          >
            mdi-plus
          </v-icon>
          Create "{{ titleCase(payeeSearch) }}"
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else>
        <v-list-item-title>No payees found</v-list-item-title>
      </v-list-item>
    </template>
    <template #append-item>
      <v-list-item
        v-if="showCreatePayeeOption && filteredPayeeOptions.length > 0"
        @click="createNewPayee"
      >
        <v-list-item-title>
          <v-icon
            start
            size="small"
          >
            mdi-plus
          </v-icon>
          Create "{{ titleCase(payeeSearch) }}"
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

