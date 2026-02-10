<script setup lang="ts">
import { useDisplay } from 'vuetify'
import type { Transaction } from '@/types'
import { useTransactionDisplay } from '@/composables/useTransactionDisplay'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'

const { mobile } = useDisplay()

const props = withDefaults(
  defineProps<{
    transaction: Transaction
    hideAccountName?: boolean
    hideDate?: boolean
  }>(),
  {
    hideAccountName: false,
    hideDate: false,
  }
)

const emit = defineEmits<{
  click: []
}>()

const { account, displayName, envelopeDisplayText, formattedDate, statusChip } =
  useTransactionDisplay(() => props.transaction)
</script>

<template>
  <!-- Mobile layout when date is in group header -->
  <v-list-item
    v-if="mobile && hideDate"
    :class="{ 'opacity-60': transaction.status === 'scheduled' }"
    class="py-2"
    @click="emit('click')"
  >
    <div class="d-flex justify-space-between align-center w-100">
      <span class="font-weight-medium text-truncate flex-shrink-1 mr-2">{{ displayName }}</span>
      <div class="d-flex align-center flex-shrink-0">
        <MoneyDisplay :amount="transaction.amount" />
        <v-icon
          v-if="transaction.is_reconciled"
          size="small"
          color="success"
          class="ml-2"
          title="Reconciled"
        >
          mdi-check-decagram
        </v-icon>
        <v-icon
          v-else
          size="small"
          :color="transaction.is_cleared ? 'success' : 'grey-lighten-1'"
          class="ml-2"
          :title="transaction.is_cleared ? 'Cleared' : 'Uncleared'"
        >
          {{ transaction.is_cleared ? 'mdi-check-circle' : 'mdi-check-circle-outline' }}
        </v-icon>
      </div>
    </div>
    <div class="d-flex align-center mt-1">
      <v-chip
        v-if="envelopeDisplayText"
        size="x-small"
        variant="tonal"
      >
        {{ envelopeDisplayText }}
      </v-chip>
      <v-chip
        v-if="statusChip"
        :color="statusChip.color"
        size="x-small"
        class="ml-1"
      >
        {{ statusChip.text }}
      </v-chip>
      <span
        v-if="!hideAccountName"
        class="text-caption text-medium-emphasis ml-2"
      >
        {{ account?.name || 'Unknown Account' }}
      </span>
    </div>
  </v-list-item>

  <!-- Desktop layout (default) -->
  <v-list-item
    v-else
    :class="{ 'opacity-60': transaction.status === 'scheduled' }"
    @click="emit('click')"
  >
    <v-list-item-title class="font-weight-medium">
      {{ displayName }}
    </v-list-item-title>

    <v-list-item-subtitle>
      <span v-if="!hideDate">{{ formattedDate }}</span>
      <template v-if="!hideAccountName">
        <span
          v-if="!hideDate"
          class="mx-1"
        >·</span>
        <span>{{ account?.name || 'Unknown Account' }}</span>
      </template>
      <template v-if="envelopeDisplayText">
        <span class="mx-1">·</span>
        <span>{{ envelopeDisplayText }}</span>
      </template>
      <v-chip
        v-if="statusChip"
        :color="statusChip.color"
        size="x-small"
        class="ml-2"
      >
        {{ statusChip.text }}
      </v-chip>
    </v-list-item-subtitle>

    <template #append>
      <div class="d-flex align-center">
        <MoneyDisplay :amount="transaction.amount" />
        <v-icon
          v-if="transaction.is_reconciled"
          size="small"
          color="success"
          class="ml-2"
          title="Reconciled"
        >
          mdi-check-decagram
        </v-icon>
        <v-icon
          v-else
          size="small"
          :color="transaction.is_cleared ? 'success' : 'grey-lighten-1'"
          class="ml-2"
          :title="transaction.is_cleared ? 'Cleared' : 'Uncleared'"
        >
          {{ transaction.is_cleared ? 'mdi-check-circle' : 'mdi-check-circle-outline' }}
        </v-icon>
      </div>
    </template>
  </v-list-item>
</template>
