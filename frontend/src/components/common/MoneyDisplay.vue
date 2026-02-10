<script setup lang="ts">
import { computed } from 'vue'
import { formatMoney, getMoneyColor } from '@/utils/money'

const props = withDefaults(
  defineProps<{
    amount: number
    colored?: boolean
    size?: 'small' | 'medium' | 'large'
  }>(),
  {
    colored: true,
    size: 'medium',
  }
)

const formattedAmount = computed(() => formatMoney(props.amount))
const colorClass = computed(() => (props.colored ? getMoneyColor(props.amount) : ''))
const sizeClass = computed(() => {
  switch (props.size) {
    case 'small':
      return 'text-body-2'
    case 'large':
      return 'text-h5'
    default:
      return 'text-body-1'
  }
})
</script>

<template>
  <span
    :class="[colorClass, sizeClass]"
    class="font-weight-medium"
  >
    {{ formattedAmount }}
  </span>
</template>
