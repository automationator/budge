<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDisplay } from 'vuetify'
import type { Transaction } from '@/types'
import TransactionItem from './TransactionItem.vue'
import TransactionTableRow from './TransactionTableRow.vue'
import { useTransactionGroups } from '@/composables/useTransactionGroups'

const { mobile } = useDisplay()

const props = withDefaults(
  defineProps<{
    transactions: Transaction[]
    loading?: boolean
    storageKey: string
    hideAccountName?: boolean
  }>(),
  {
    loading: false,
    hideAccountName: false,
  }
)

const emit = defineEmits<{
  'transaction-click': [transactionId: string]
}>()

// Collapse state with localStorage persistence
const isCollapsed = ref(false)

onMounted(() => {
  try {
    const stored = localStorage.getItem(props.storageKey)
    if (stored !== null) {
      isCollapsed.value = stored === 'true'
    }
  } catch {
    // Ignore localStorage errors
  }
})

watch(isCollapsed, (newValue) => {
  try {
    localStorage.setItem(props.storageKey, String(newValue))
  } catch {
    // Ignore localStorage errors
  }
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

// Use shared composable for grouping transactions by date
const transactionsRef = computed(() => props.transactions)
const { groupedTransactions } = useTransactionGroups({
  transactions: transactionsRef,
  sortOrder: 'ascending',
  dateMode: 'future',
})
</script>

<template>
  <div
    v-if="transactions.length > 0 || loading"
    class="mb-4"
  >
    <!-- Section Header -->
    <div
      class="d-flex align-center mb-2 px-2 upcoming-header"
      @click="toggleCollapse"
    >
      <v-icon
        size="small"
        class="mr-1 collapse-chevron"
        :class="{ 'rotate-collapsed': isCollapsed }"
      >
        mdi-chevron-down
      </v-icon>
      <v-icon
        size="small"
        class="mr-2"
        color="warning"
      >
        mdi-calendar-clock
      </v-icon>
      <span class="text-subtitle-2 text-grey">Upcoming</span>
      <v-chip
        v-if="transactions.length > 0"
        size="x-small"
        class="ml-2"
        color="warning"
        variant="tonal"
      >
        {{ transactions.length }}
      </v-chip>
    </div>

    <!-- Content -->
    <v-expand-transition>
      <div v-show="!isCollapsed">
        <!-- Loading State -->
        <div
          v-if="loading && transactions.length === 0"
          class="text-center py-4"
        >
          <v-progress-circular
            indeterminate
            color="warning"
            size="24"
          />
        </div>

        <!-- Mobile: Transaction Groups - unified in a single card -->
        <v-card
          v-else-if="mobile"
          variant="outlined"
        >
          <div
            v-for="(group, groupIndex) in groupedTransactions"
            :key="group.date"
          >
            <v-divider v-if="groupIndex > 0" />
            <div class="text-subtitle-2 text-medium-emphasis px-4 pt-3 pb-1">
              {{ group.formattedDate }}
            </div>
            <v-list density="compact">
              <template
                v-for="(transaction, index) in group.transactions"
                :key="transaction.id"
              >
                <v-divider
                  v-if="index > 0"
                  class="mx-3"
                />
                <TransactionItem
                  :transaction="transaction"
                  :hide-account-name="hideAccountName"
                  @click="emit('transaction-click', transaction.id)"
                />
              </template>
            </v-list>
          </div>
        </v-card>

        <!-- Desktop: Table view -->
        <v-card
          v-else
          variant="outlined"
        >
          <v-table density="comfortable">
            <thead>
              <tr>
                <th style="width: 100px">
                  Date
                </th>
                <th>Payee</th>
                <th style="width: 180px">
                  Envelope
                </th>
                <th style="width: 200px">
                  Memo
                </th>
                <th
                  style="width: 120px"
                  class="text-right"
                >
                  Amount
                </th>
                <th
                  style="width: 60px"
                  class="text-center"
                />
              </tr>
            </thead>
            <tbody>
              <TransactionTableRow
                v-for="txn in transactions"
                :key="txn.id"
                :transaction="txn"
                :hide-account-name="hideAccountName"
                @click="emit('transaction-click', txn.id)"
              />
            </tbody>
          </v-table>
        </v-card>
      </div>
    </v-expand-transition>
  </div>
</template>

<style scoped>
.upcoming-header {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
}

.upcoming-header:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.collapse-chevron {
  transition: transform 200ms ease-in-out;
}

.rotate-collapsed {
  transform: rotate(-90deg);
}
</style>
