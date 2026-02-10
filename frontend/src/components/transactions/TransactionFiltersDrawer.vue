<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePayeesStore } from '@/stores/payees'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import LocationSelect from '@/components/common/LocationSelect.vue'

export interface TransactionFilters {
  payeeId: string | null
  locationId: string | null
  envelopeId: string | null
  hideReconciled: boolean
  includeInBudget: boolean | null // null = all, true = budget only, false = tracking only
  needsReview: boolean // filter to unallocated expenses on budget accounts
}

const props = defineProps<{
  modelValue: boolean
  filters: TransactionFilters
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:filters': [filters: TransactionFilters]
}>()

const payeesStore = usePayeesStore()

// Local state for form fields
const localPayeeId = ref<string | null>(null)
const localLocationId = ref<string | null>(null)
const localEnvelopeId = ref<string | null>(null)
const localHideReconciled = ref(false)
const localAccountType = ref<'all' | 'budget' | 'tracking'>('all')
const localNeedsReview = ref(false)

// Sync local state with props
watch(
  () => props.filters,
  (filters) => {
    localPayeeId.value = filters.payeeId
    localLocationId.value = filters.locationId
    localEnvelopeId.value = filters.envelopeId
    localHideReconciled.value = filters.hideReconciled
    localAccountType.value =
      filters.includeInBudget === null
        ? 'all'
        : filters.includeInBudget
          ? 'budget'
          : 'tracking'
    localNeedsReview.value = filters.needsReview
  },
  { immediate: true }
)

const drawerOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const payeeOptions = computed(() =>
  payeesStore.sortedPayees.map((p) => ({
    title: p.name,
    value: p.id,
  }))
)

// Count active filters
const activeFilterCount = computed(() => {
  let count = 0
  if (props.filters.payeeId) count++
  if (props.filters.locationId) count++
  if (props.filters.envelopeId && !props.filters.needsReview) count++ // Don't double-count envelope when needsReview
  if (props.filters.hideReconciled) count++
  if (props.filters.includeInBudget !== null && !props.filters.needsReview) count++ // Don't double-count when needsReview
  if (props.filters.needsReview) count++
  return count
})

function applyFilters() {
  emit('update:filters', {
    payeeId: localPayeeId.value,
    locationId: localLocationId.value,
    envelopeId: localEnvelopeId.value,
    hideReconciled: localHideReconciled.value,
    includeInBudget:
      localAccountType.value === 'all'
        ? null
        : localAccountType.value === 'budget',
    needsReview: localNeedsReview.value,
  })
  drawerOpen.value = false
}

function clearFilters() {
  localPayeeId.value = null
  localLocationId.value = null
  localEnvelopeId.value = null
  localHideReconciled.value = false
  localAccountType.value = 'all'
  localNeedsReview.value = false
}

function clearAndApply() {
  clearFilters()
  emit('update:filters', {
    payeeId: null,
    locationId: null,
    envelopeId: null,
    hideReconciled: false,
    includeInBudget: null,
    needsReview: false,
  })
  drawerOpen.value = false
}

defineExpose({
  activeFilterCount,
})
</script>

<template>
  <v-bottom-sheet v-model="drawerOpen">
    <v-card>
      <v-card-title class="d-flex align-center">
        <span>Filters</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          @click="drawerOpen = false"
        />
      </v-card-title>

      <v-card-text>
        <!-- Needs Review Filter -->
        <v-switch
          v-model="localNeedsReview"
          label="Needs Review Only"
          color="primary"
          hide-details
          density="comfortable"
          class="mb-4"
        />

        <!-- Payee Filter -->
        <v-autocomplete
          v-model="localPayeeId"
          :items="payeeOptions"
          label="Payee"
          clearable
          hide-details
          density="comfortable"
          class="mb-4"
        />

        <!-- Location Filter -->
        <LocationSelect
          v-model="localLocationId"
          label="Location"
          clearable
          hide-details
          density="comfortable"
          class="mb-4"
          :allow-create="false"
        />

        <!-- Envelope Filter -->
        <EnvelopeSelect
          v-model="localEnvelopeId"
          clearable
          hide-details
          density="comfortable"
          class="mb-4"
        />

        <!-- Toggle Filters -->
        <v-switch
          v-model="localHideReconciled"
          label="Hide Reconciled"
          color="success"
          hide-details
          density="comfortable"
          class="mb-4"
        />

        <!-- Account Type Filter -->
        <div class="text-subtitle-2 mb-2">
          Account Type
        </div>
        <v-radio-group
          v-model="localAccountType"
          hide-details
          density="comfortable"
          class="mb-4"
        >
          <v-radio
            label="All Accounts"
            value="all"
          />
          <v-radio
            label="Budget Accounts Only"
            value="budget"
          />
          <v-radio
            label="Tracking Accounts Only"
            value="tracking"
          />
        </v-radio-group>
      </v-card-text>

      <v-card-actions class="px-4 pb-4">
        <v-btn
          variant="text"
          @click="clearAndApply"
        >
          Clear All
        </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          @click="applyFilters"
        >
          Apply Filters
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-bottom-sheet>
</template>
