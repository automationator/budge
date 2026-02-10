<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { EnvelopeActivityResponse } from '@/api/envelopes'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import { useEnvelopesStore } from '@/stores/envelopes'

const props = defineProps<{
  modelValue: boolean
  envelopeId: string | null
  envelopeName: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const store = useEnvelopesStore()
const activity = ref<EnvelopeActivityResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Fetch activity when dialog opens
watch(
  () => props.modelValue && props.envelopeId,
  async (shouldFetch) => {
    if (shouldFetch && props.envelopeId) {
      loading.value = true
      error.value = null
      try {
        activity.value = await store.fetchEnvelopeActivity(props.envelopeId)
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load activity'
      } finally {
        loading.value = false
      }
    }
  },
  { immediate: true }
)

// Reset when dialog closes
watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      activity.value = null
      error.value = null
    }
  }
)

function close() {
  emit('update:modelValue', false)
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getTransferLabel(item: EnvelopeActivityResponse['items'][0]): string {
  const counterpart = item.counterpart_envelope_name || 'Unknown'
  // When counterpart is Unallocated and there's a memo, use the memo as label
  // (e.g., "Credit card payment" instead of "Transfer to Unallocated")
  if (counterpart === 'Unallocated' && item.memo) {
    return item.memo
  }
  if (item.amount > 0) {
    return `Transfer from ${counterpart}`
  } else {
    return `Transfer to ${counterpart}`
  }
}

function isTransferMemoUsedAsLabel(item: EnvelopeActivityResponse['items'][0]): boolean {
  const counterpart = item.counterpart_envelope_name || 'Unknown'
  return counterpart === 'Unallocated' && !!item.memo
}

const positiveTotal = computed(() => {
  if (!activity.value) return 0
  return activity.value.items
    .filter(item => item.amount > 0)
    .reduce((sum, item) => sum + item.amount, 0)
})

const negativeTotal = computed(() => {
  if (!activity.value) return 0
  return activity.value.items
    .filter(item => item.amount < 0)
    .reduce((sum, item) => sum + item.amount, 0)
})
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <span>{{ envelopeName }} Activity</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          @click="close"
        />
      </v-card-title>

      <v-card-subtitle v-if="activity">
        {{ formatDate(activity.start_date) }} - {{ formatDate(activity.end_date) }}
      </v-card-subtitle>

      <v-divider />

      <v-card-text class="pa-0">
        <!-- Loading State -->
        <div
          v-if="loading"
          class="d-flex justify-center align-center py-8"
        >
          <v-progress-circular
            indeterminate
            color="primary"
          />
        </div>

        <!-- Error State -->
        <v-alert
          v-else-if="error"
          type="error"
          class="ma-4"
        >
          {{ error }}
        </v-alert>

        <!-- Empty State -->
        <div
          v-else-if="activity && activity.items.length === 0"
          class="text-center py-8 text-medium-emphasis"
        >
          No activity in this period
        </div>

        <!-- Activity List -->
        <v-list
          v-else-if="activity"
          lines="two"
          density="compact"
        >
          <v-list-item
            v-for="item in activity.items"
            :key="item.allocation_id"
          >
            <template #prepend>
              <div class="activity-date text-caption text-medium-emphasis">
                {{ formatDate(item.date) }}
              </div>
            </template>

            <!-- Transaction activity -->
            <template v-if="item.activity_type === 'transaction'">
              <v-list-item-title>
                {{ item.payee_name || 'No payee' }}
              </v-list-item-title>

              <v-list-item-subtitle>
                {{ item.account_name }}
                <span v-if="item.memo"> - {{ item.memo }}</span>
              </v-list-item-subtitle>
            </template>

            <!-- Transfer activity -->
            <template v-else>
              <v-list-item-title class="d-flex align-center">
                <v-icon
                  size="small"
                  class="mr-1"
                >
                  mdi-swap-horizontal
                </v-icon>
                {{ getTransferLabel(item) }}
              </v-list-item-title>

              <v-list-item-subtitle v-if="item.memo && !isTransferMemoUsedAsLabel(item)">
                {{ item.memo }}
              </v-list-item-subtitle>
            </template>

            <template #append>
              <MoneyDisplay
                :amount="item.amount"
                size="small"
              />
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>

      <v-divider v-if="activity && activity.items.length > 0" />

      <!-- Totals Footer -->
      <v-card-actions
        v-if="activity && activity.items.length > 0"
        class="flex-column align-stretch px-4"
      >
        <div
          v-if="positiveTotal > 0"
          class="d-flex justify-space-between py-1"
        >
          <span class="text-body-2 text-medium-emphasis">Inflows</span>
          <MoneyDisplay
            :amount="positiveTotal"
            size="small"
          />
        </div>
        <div
          v-if="negativeTotal < 0"
          class="d-flex justify-space-between py-1"
        >
          <span class="text-body-2 text-medium-emphasis">Outflows</span>
          <MoneyDisplay
            :amount="negativeTotal"
            size="small"
          />
        </div>
        <div class="d-flex justify-space-between py-1">
          <span class="text-body-2 font-weight-medium">Total</span>
          <MoneyDisplay
            :amount="activity.total"
            size="medium"
          />
        </div>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.activity-date {
  width: 50px;
  text-align: right;
  margin-right: 16px;
}
</style>
