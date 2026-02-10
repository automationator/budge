<script setup lang="ts">
import { computed } from 'vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import { useEnvelopesStore } from '@/stores/envelopes'

const store = useEnvelopesStore()

const summary = computed(() => store.budgetSummary)

// Format date range for display
const dateRangeDisplay = computed(() => {
  if (!summary.value) return ''
  const start = new Date(summary.value.start_date + 'T00:00:00')
  const end = new Date(summary.value.end_date + 'T00:00:00')

  const formatOptions: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  return `${start.toLocaleDateString('en-US', formatOptions)} - ${end.toLocaleDateString('en-US', formatOptions)}`
})

</script>

<template>
  <v-card
    v-if="summary"
    variant="outlined"
    class="budget-summary-panel"
  >
    <v-card-title class="text-subtitle-1 pb-2">
      Summary
    </v-card-title>

    <v-card-subtitle class="pb-3">
      {{ dateRangeDisplay }}
    </v-card-subtitle>

    <v-divider />

    <v-card-text class="pt-4">
      <!-- Ready to Assign -->
      <div class="summary-row mb-4">
        <div class="summary-label text-body-2">
          Ready to Assign
        </div>
        <MoneyDisplay
          :amount="summary.ready_to_assign"
          size="large"
          class="summary-value"
        />
      </div>

      <v-divider class="mb-4" />

      <!-- Period Metrics -->
      <div class="summary-row mb-3">
        <div class="summary-label text-body-2 text-medium-emphasis">
          Activity
        </div>
        <MoneyDisplay
          :amount="summary.total_activity"
          size="small"
        />
      </div>

      <v-divider class="my-4" />

      <!-- Total Balance -->
      <div class="summary-row">
        <div class="summary-label text-body-2 font-weight-medium">
          Total Budgeted
        </div>
        <MoneyDisplay
          :amount="summary.total_balance"
          size="medium"
          :colored="false"
        />
      </div>
    </v-card-text>
  </v-card>

  <!-- Loading State -->
  <v-card
    v-else-if="store.budgetSummaryLoading"
    variant="outlined"
    class="budget-summary-panel"
  >
    <v-card-text class="d-flex justify-center align-center py-8">
      <v-progress-circular
        indeterminate
        color="primary"
        size="32"
      />
    </v-card-text>
  </v-card>
</template>

<style scoped>
.budget-summary-panel {
  position: sticky;
  top: 80px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-label {
  flex: 1;
}

.summary-value {
  text-align: right;
}
</style>
