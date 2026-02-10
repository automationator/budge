<script setup lang="ts">
import { computed } from 'vue'
import type { Account } from '@/types'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'

const props = defineProps<{
  account: Account
}>()

const emit = defineEmits<{
  click: []
  edit: []
}>()

const icon = computed(() => {
  // Default icons by account type
  if (props.account.icon) return props.account.icon
  switch (props.account.account_type) {
    case 'checking':
      return 'mdi-bank'
    case 'savings':
      return 'mdi-piggy-bank'
    case 'credit_card':
      return 'mdi-credit-card'
    case 'cash':
      return 'mdi-cash'
    case 'investment':
      return 'mdi-chart-line'
    case 'loan':
      return 'mdi-hand-coin'
    default:
      return 'mdi-wallet'
  }
})

const isEmoji = computed(() => {
  // MDI icons start with 'mdi-', everything else is treated as emoji
  return icon.value && !icon.value.startsWith('mdi-')
})

const accountTypeLabel = computed(() => {
  switch (props.account.account_type) {
    case 'checking':
      return 'Checking'
    case 'savings':
      return 'Savings'
    case 'credit_card':
      return 'Credit Card'
    case 'cash':
      return 'Cash'
    case 'investment':
      return 'Investment'
    case 'loan':
      return 'Loan'
    default:
      return 'Other'
  }
})
</script>

<template>
  <v-card
    :class="{ 'opacity-60': !account.is_active }"
    @click="emit('click')"
  >
    <v-card-item>
      <template #prepend>
        <v-avatar
          color="primary"
          variant="tonal"
        >
          <span
            v-if="isEmoji"
            class="text-h6"
          >{{ icon }}</span>
          <v-icon v-else>
            {{ icon }}
          </v-icon>
        </v-avatar>
      </template>

      <v-card-title>{{ account.name }}</v-card-title>
      <v-card-subtitle>{{ accountTypeLabel }}</v-card-subtitle>

      <template #append>
        <div class="text-right">
          <MoneyDisplay
            :amount="account.cleared_balance + account.uncleared_balance"
            size="large"
          />
          <div
            v-if="!account.include_in_budget"
            class="text-caption text-grey"
          >
            Off-budget
          </div>
        </div>
      </template>
    </v-card-item>

    <v-card-actions v-if="$slots.actions">
      <slot name="actions" />
    </v-card-actions>
  </v-card>
</template>
