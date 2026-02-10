<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'funded' | 'needs_attention' | 'partially_funded' | 'not_linked'
  size?: 'x-small' | 'small' | 'default'
}>()

const chipConfig = computed(() => {
  switch (props.status) {
    case 'funded':
      return { color: 'success', icon: 'mdi-check-circle', text: 'Funded' }
    case 'needs_attention':
      return { color: 'warning', icon: 'mdi-alert-circle', text: 'Needs Attention' }
    case 'partially_funded':
      return { color: 'warning', icon: 'mdi-alert-circle', text: 'Partial' }
    case 'not_linked':
    default:
      return { color: 'grey', icon: 'mdi-link-off', text: 'Not Linked' }
  }
})
</script>

<template>
  <v-chip
    :color="chipConfig.color"
    :size="size || 'small'"
    variant="tonal"
  >
    <v-icon
      :icon="chipConfig.icon"
      size="small"
      start
    />
    {{ chipConfig.text }}
  </v-chip>
</template>
