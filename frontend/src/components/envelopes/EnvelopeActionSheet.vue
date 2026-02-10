<script setup lang="ts">
import type { EnvelopeBudgetItem } from '@/api/envelopes'

defineProps<{
  modelValue: boolean
  envelope: EnvelopeBudgetItem | null
  isCreditCard: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  transfer: []
  addTransaction: []
  viewActivity: []
  viewDetails: []
}>()

function handleAction(action: () => void) {
  action()
}
</script>

<template>
  <v-bottom-sheet
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card v-if="envelope">
      <v-card-title class="d-flex align-center">
        <v-avatar
          color="primary"
          variant="tonal"
          size="36"
          class="mr-3"
        >
          <span
            v-if="envelope.icon && !envelope.icon.startsWith('mdi-')"
            class="emoji-icon"
          >
            {{ envelope.icon }}
          </span>
          <v-icon
            v-else
            size="small"
          >
            {{ envelope.icon || (isCreditCard ? 'mdi-credit-card' : 'mdi-wallet') }}
          </v-icon>
        </v-avatar>
        {{ envelope.envelope_name }}
      </v-card-title>

      <!-- Prominent Add Transaction button -->
      <v-btn
        v-if="!isCreditCard"
        variant="elevated"
        color="primary"
        block
        class="mx-4 mb-3"
        style="width: calc(100% - 32px)"
        @click="handleAction(() => emit('addTransaction'))"
      >
        <v-icon start>
          mdi-plus
        </v-icon>
        Add Transaction
      </v-btn>

      <v-list>
        <v-list-item @click="handleAction(() => emit('transfer'))">
          <template #prepend>
            <v-icon>mdi-swap-horizontal</v-icon>
          </template>
          <v-list-item-title>Transfer Money</v-list-item-title>
        </v-list-item>

        <v-list-item @click="handleAction(() => emit('viewActivity'))">
          <template #prepend>
            <v-icon>mdi-history</v-icon>
          </template>
          <v-list-item-title>View Activity</v-list-item-title>
        </v-list-item>

        <v-list-item @click="handleAction(() => emit('viewDetails'))">
          <template #prepend>
            <v-icon>mdi-open-in-new</v-icon>
          </template>
          <v-list-item-title>View Details</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>
  </v-bottom-sheet>
</template>

<style scoped>
.emoji-icon {
  font-size: 18px;
  line-height: 1;
}
</style>
