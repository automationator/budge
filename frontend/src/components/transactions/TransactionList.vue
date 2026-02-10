<script setup lang="ts">
import { computed } from 'vue'
import { useDisplay } from 'vuetify'
import type { Transaction } from '@/types'
import TransactionItem from '@/components/transactions/TransactionItem.vue'
import TransactionTableRow from '@/components/transactions/TransactionTableRow.vue'
import { useTransactionGroups } from '@/composables/useTransactionGroups'

const { mobile } = useDisplay()

const props = withDefaults(
  defineProps<{
    transactions: Transaction[]
    loading?: boolean
    hasMore?: boolean
    hideAccountName?: boolean
    emptyMessage?: string
    emptyIcon?: string
  }>(),
  {
    loading: false,
    hasMore: false,
    hideAccountName: false,
    emptyMessage: 'No transactions yet.',
    emptyIcon: 'mdi-swap-horizontal',
  }
)

const emit = defineEmits<{
  'transaction-click': [transactionId: string]
  'load-more': []
}>()

// Use shared composable for grouping transactions by date
const transactionsRef = computed(() => props.transactions)
const { groupedTransactions } = useTransactionGroups({
  transactions: transactionsRef,
  sortOrder: 'descending',
  dateMode: 'past',
})
</script>

<template>
  <!-- Loading State -->
  <div
    v-if="loading && transactions.length === 0"
    class="text-center py-8"
  >
    <v-progress-circular
      indeterminate
      color="primary"
    />
  </div>

  <!-- Empty State -->
  <v-card v-else-if="transactions.length === 0">
    <v-card-text class="text-center text-grey py-8">
      <v-icon
        size="64"
        color="grey-lighten-1"
      >
        {{ emptyIcon }}
      </v-icon>
      <p class="mt-4">
        {{ emptyMessage }}
      </p>
      <slot name="empty-action" />
    </v-card-text>
  </v-card>

  <!-- Transaction List -->
  <template v-else>
    <!-- Mobile: Each date group gets its own card -->
    <template v-if="mobile">
      <div
        v-for="group in groupedTransactions"
        :key="group.date"
        class="mb-4"
      >
        <h3 class="text-subtitle-2 text-medium-emphasis mb-2 px-2">
          {{ group.formattedDate }}
        </h3>
        <v-card>
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
                hide-date
                @click="emit('transaction-click', transaction.id)"
              />
            </template>
          </v-list>
        </v-card>
      </div>
    </template>

    <!-- Desktop: Table view -->
    <template v-else>
      <v-card>
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
            <!-- No date header rows - the Date column provides context -->
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
    </template>

    <!-- Load More -->
    <div
      v-if="hasMore"
      class="text-center py-4"
    >
      <v-btn
        variant="outlined"
        :loading="loading"
        @click="emit('load-more')"
      >
        Load More
      </v-btn>
    </div>
  </template>
</template>

<style scoped>
.date-header-row {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
}
.date-header-row td {
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>
