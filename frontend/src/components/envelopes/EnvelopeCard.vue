<script setup lang="ts">
import { toRef } from 'vue'
import type { Envelope } from '@/types'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import EnvelopeRuleIcons from '@/components/envelopes/EnvelopeRuleIcons.vue'
import { useEnvelopeProgress } from '@/composables/useEnvelopeProgress'

const props = defineProps<{
  envelope: Envelope
  editMode?: boolean
  isFirst?: boolean
  isLast?: boolean
  reorderLoading?: boolean
}>()

const emit = defineEmits<{
  click: []
  transfer: []
  addTransaction: []
  moveUp: []
  moveDown: []
}>()

const { progressPercent, progressColor, balanceColor } = useEnvelopeProgress(toRef(props, 'envelope'))
</script>

<template>
  <v-list-item
    class="py-3"
    @click="emit('click')"
  >
    <template #prepend>
      <v-avatar
        color="primary"
        variant="tonal"
        size="40"
      >
        <v-icon>{{ envelope.icon || 'mdi-wallet' }}</v-icon>
      </v-avatar>
    </template>

    <v-list-item-title class="font-weight-medium d-flex align-center gap-2">
      {{ envelope.name }}
      <EnvelopeRuleIcons :envelope-id="envelope.id" />
    </v-list-item-title>

    <v-list-item-subtitle v-if="envelope.target_balance">
      <v-progress-linear
        :model-value="progressPercent ?? 0"
        :color="progressColor"
        height="4"
        rounded
        class="mt-1"
      />
      <span class="text-caption">
        <MoneyDisplay
          :amount="envelope.current_balance"
          :class="balanceColor ? `text-${balanceColor}` : ''"
        />
        of
        <MoneyDisplay :amount="envelope.target_balance" />
      </span>
    </v-list-item-subtitle>

    <template #append>
      <div class="d-flex align-center gap-2">
        <!-- Edit mode: show reorder buttons -->
        <template v-if="editMode">
          <v-btn
            icon="mdi-chevron-up"
            size="small"
            variant="text"
            :disabled="isFirst || reorderLoading"
            @click.stop="emit('moveUp')"
          />
          <v-btn
            icon="mdi-chevron-down"
            size="small"
            variant="text"
            :disabled="isLast || reorderLoading"
            @click.stop="emit('moveDown')"
          />
        </template>

        <!-- Normal mode: show action buttons -->
        <template v-else>
          <MoneyDisplay
            v-if="!envelope.target_balance"
            :amount="envelope.current_balance"
            class="text-body-1 font-weight-medium"
            :class="balanceColor ? `text-${balanceColor}` : ''"
          />
          <v-tooltip
            text="Transfer"
            location="top"
          >
            <template #activator="{ props: tooltipProps }">
              <v-btn
                v-bind="tooltipProps"
                icon="mdi-swap-horizontal"
                size="small"
                variant="text"
                @click.stop="emit('transfer')"
              />
            </template>
          </v-tooltip>
          <v-tooltip
            text="Add Transaction"
            location="top"
          >
            <template #activator="{ props: tooltipProps }">
              <v-btn
                v-bind="tooltipProps"
                icon="mdi-plus"
                size="small"
                variant="text"
                @click.stop="emit('addTransaction')"
              />
            </template>
          </v-tooltip>
        </template>
      </div>
    </template>
  </v-list-item>
</template>
