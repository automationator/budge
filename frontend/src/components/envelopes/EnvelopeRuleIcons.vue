<script setup lang="ts">
import { computed } from 'vue'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import type { AllocationRuleType } from '@/types'

const props = defineProps<{
  envelopeId: string
}>()

const allocationRulesStore = useAllocationRulesStore()

const rulesForEnvelope = computed(() => {
  return allocationRulesStore.rulesByEnvelope[props.envelopeId] || []
})

const activeRulesForEnvelope = computed(() => {
  return rulesForEnvelope.value.filter((r) => r.is_active)
})

// Get unique rule types that are active for this envelope
const uniqueRuleTypes = computed(() => {
  const types = new Set<AllocationRuleType>()
  for (const rule of activeRulesForEnvelope.value) {
    types.add(rule.rule_type)
  }
  return Array.from(types)
})

function getRuleTypeIcon(type: AllocationRuleType): string {
  switch (type) {
    case 'fill_to_target':
      return 'mdi-target'
    case 'fixed':
      return 'mdi-currency-usd'
    case 'percentage':
      return 'mdi-percent'
    case 'remainder':
      return 'mdi-scale-balance'
    case 'period_cap':
      return 'mdi-speedometer'
  }
}

function getRuleTypeTooltip(type: AllocationRuleType): string {
  switch (type) {
    case 'fill_to_target':
      return 'Fill to target'
    case 'fixed':
      return 'Fixed amount'
    case 'percentage':
      return 'Percentage'
    case 'remainder':
      return 'Remainder'
    case 'period_cap':
      return 'Period cap'
  }
}
</script>

<template>
  <div
    v-if="uniqueRuleTypes.length > 0"
    class="d-inline-flex align-center gap-1 ml-2"
  >
    <v-tooltip
      v-for="type in uniqueRuleTypes"
      :key="type"
      :text="getRuleTypeTooltip(type)"
      location="top"
    >
      <template #activator="{ props: tooltipProps }">
        <v-icon
          v-bind="tooltipProps"
          :icon="getRuleTypeIcon(type)"
          size="x-small"
          color="grey"
        />
      </template>
    </v-tooltip>
  </div>
</template>
