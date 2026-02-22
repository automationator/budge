<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { DateRangePreset } from '@/stores/envelopes'

const props = defineProps<{
  startDate: string
  endDate: string
  preset: DateRangePreset
}>()

const emit = defineEmits<{
  'update:preset': [value: DateRangePreset]
  'update:customRange': [startDate: string, endDate: string]
}>()

const menuOpen = ref(false)
const showCustomDialog = ref(false)
const customStartDate = ref(props.startDate)
const customEndDate = ref(props.endDate)

const presetOptions = [
  { value: 'this_month', title: 'This Month' },
  { value: 'last_month', title: 'Last Month' },
  { value: 'last_3_months', title: 'Last 3 Months' },
  { value: 'year_to_date', title: 'Year to Date' },
  { value: 'custom', title: 'Custom...' },
] as const

const currentPresetLabel = computed(() => {
  if (props.preset === 'custom') {
    return `${formatDisplayDate(props.startDate)} - ${formatDisplayDate(props.endDate)}`
  }
  return presetOptions.find((o) => o.value === props.preset)?.title || 'This Month'
})

function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function selectPreset(preset: DateRangePreset) {
  if (preset === 'custom') {
    customStartDate.value = props.startDate
    customEndDate.value = props.endDate
    showCustomDialog.value = true
  } else {
    emit('update:preset', preset)
  }
  menuOpen.value = false
}

function applyCustomRange() {
  emit('update:customRange', customStartDate.value, customEndDate.value)
  showCustomDialog.value = false
}

// Sync custom dates when props change
watch(
  () => [props.startDate, props.endDate] as const,
  ([start, end]) => {
    customStartDate.value = start
    customEndDate.value = end
  }
)
</script>

<template>
  <v-menu
    v-model="menuOpen"
    :close-on-content-click="false"
    location="bottom end"
  >
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        variant="outlined"
        size="small"
        append-icon="mdi-chevron-down"
      >
        <v-icon
          start
          size="small"
        >
          mdi-calendar
        </v-icon>
        {{ currentPresetLabel }}
      </v-btn>
    </template>

    <v-list density="compact">
      <v-list-item
        v-for="option in presetOptions"
        :key="option.value"
        :active="preset === option.value"
        @click="selectPreset(option.value)"
      >
        <v-list-item-title>{{ option.title }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>

  <!-- Custom Date Range Dialog -->
  <v-dialog
    v-model="showCustomDialog"
    max-width="400"
  >
    <v-card rounded="xl">
      <v-card-title>Custom Date Range</v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <v-text-field
              v-model="customStartDate"
              label="Start Date"
              type="date"
              density="compact"
            />
          </v-col>
          <v-col cols="12">
            <v-text-field
              v-model="customEndDate"
              label="End Date"
              type="date"
              density="compact"
            />
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="showCustomDialog = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          class="create-btn"
          @click="applyCustomRange"
        >
          Apply
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
