<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLocationsStore } from '@/stores/locations'
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
    prependInnerIcon?: string
  }>(),
  {
    label: 'Location',
    hint: undefined,
    persistentHint: false,
    clearable: false,
    disabled: false,
    density: 'default',
    hideDetails: false,
    rules: () => [],
    allowCreate: true,
    prependInnerIcon: undefined,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const locationsStore = useLocationsStore()

// Search state
const locationSearch = ref('')

// Create state
const creating = ref(false)

// Autocomplete ref for closing menu
const autocompleteRef = ref<{ blur: () => void } | null>(null)

const selectedValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const locationOptions = computed(() =>
  locationsStore.sortedLocations.map((l) => ({ title: l.name, value: l.id }))
)

const filteredLocationOptions = computed(() => {
  if (!locationSearch.value) return locationOptions.value
  const search = locationSearch.value.toLowerCase()
  return locationOptions.value.filter((l) => l.title.toLowerCase().includes(search))
})

const showCreateLocationOption = computed(() => {
  if (!props.allowCreate || !locationSearch.value || creating.value) return false
  const search = locationSearch.value.toLowerCase()
  return !locationOptions.value.some((l) => l.title.toLowerCase() === search)
})

async function createNewLocation() {
  if (!locationSearch.value.trim() || creating.value) return

  try {
    creating.value = true
    const location = await locationsStore.createLocation({ name: locationSearch.value.trim() })
    selectedValue.value = location.id
    locationSearch.value = ''
    // Close the dropdown menu
    autocompleteRef.value?.blur()
  } catch {
    showSnackbar('Failed to create location', 'error')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <v-autocomplete
    ref="autocompleteRef"
    v-model="selectedValue"
    v-model:search="locationSearch"
    :label="label"
    :items="filteredLocationOptions"
    :hint="hint"
    :persistent-hint="persistentHint"
    :clearable="clearable"
    :disabled="disabled"
    :density="density"
    :hide-details="hideDetails"
    :rules="rules"
    :prepend-inner-icon="prependInnerIcon"
    auto-select-first
  >
    <template #no-data>
      <v-list-item
        v-if="showCreateLocationOption"
        @click="createNewLocation"
      >
        <v-list-item-title>
          <v-icon
            start
            size="small"
          >
            mdi-plus
          </v-icon>
          Create "{{ locationSearch }}"
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else>
        <v-list-item-title>No locations found</v-list-item-title>
      </v-list-item>
    </template>
    <template #append-item>
      <v-list-item
        v-if="showCreateLocationOption && filteredLocationOptions.length > 0"
        @click="createNewLocation"
      >
        <v-list-item-title>
          <v-icon
            start
            size="small"
          >
            mdi-plus
          </v-icon>
          Create "{{ locationSearch }}"
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>
