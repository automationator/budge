<script setup lang="ts">
import type { Transaction } from '@/types'
import { useTransactionDisplay } from '@/composables/useTransactionDisplay'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'

const props = withDefaults(
  defineProps<{
    transaction: Transaction
    hideAccountName?: boolean
  }>(),
  {
    hideAccountName: false,
  }
)

const emit = defineEmits<{
  click: []
}>()

const { account, displayName, envelopeDisplayText, formattedDate, statusChip } =
  useTransactionDisplay(() => props.transaction)
</script>

<template>
  <tr
    class="transaction-row"
    :class="{ 'opacity-60': transaction.status === 'scheduled' }"
    @click="emit('click')"
  >
    <!-- Date -->
    <td class="text-no-wrap">
      {{ formattedDate }}
    </td>

    <!-- Payee -->
    <td>
      <span class="font-weight-medium">{{ displayName }}</span>
      <v-chip
        v-if="statusChip"
        :color="statusChip.color"
        size="x-small"
        class="ml-2"
      >
        {{ statusChip.text }}
      </v-chip>
      <span
        v-if="!hideAccountName"
        class="text-medium-emphasis ml-2"
      >
        {{ account?.name || 'Unknown Account' }}
      </span>
    </td>

    <!-- Envelope -->
    <td>{{ envelopeDisplayText || '-' }}</td>

    <!-- Memo -->
    <td class="memo-cell text-medium-emphasis">
      {{ transaction.memo || '' }}
    </td>

    <!-- Amount -->
    <td class="text-right text-no-wrap">
      <MoneyDisplay :amount="transaction.amount" />
    </td>

    <!-- Cleared Status -->
    <td class="text-center">
      <v-icon
        v-if="transaction.is_reconciled"
        size="small"
        color="success"
        title="Reconciled"
      >
        mdi-check-decagram
      </v-icon>
      <v-icon
        v-else
        size="small"
        :color="transaction.is_cleared ? 'success' : 'grey-lighten-1'"
        :title="transaction.is_cleared ? 'Cleared' : 'Uncleared'"
      >
        {{ transaction.is_cleared ? 'mdi-check-circle' : 'mdi-check-circle-outline' }}
      </v-icon>
    </td>
  </tr>
</template>

<style scoped>
.transaction-row:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
  cursor: pointer;
}

.memo-cell {
  max-width: 200px;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}
</style>
