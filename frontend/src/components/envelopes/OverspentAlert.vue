<script setup lang="ts">
import { computed } from 'vue'
import { useEnvelopesStore } from '@/stores/envelopes'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'

const emit = defineEmits<{
  (e: 'cover-envelope', envelopeId: string): void
}>()

const envelopesStore = useEnvelopesStore()

const overspentEnvelopes = computed(() => envelopesStore.overspentEnvelopes)

const hasOverspent = computed(() => overspentEnvelopes.value.length > 0)

function getEnvelopeIcon(envelope: { icon?: string | null }): string {
  return envelope.icon || 'mdi-email-outline'
}
</script>

<template>
  <v-alert
    v-if="hasOverspent"
    type="warning"
    variant="tonal"
    prominent
    class="mb-4"
    data-testid="overspent-alert"
  >
    <template #title>
      Overspent Envelopes
    </template>

    <div class="mb-3">
      You've spent more than budgeted in the following envelopes.
      Move money from other envelopes to cover overspending.
    </div>

    <v-list
      density="compact"
      class="bg-transparent"
    >
      <v-list-item
        v-for="envelope in overspentEnvelopes"
        :key="envelope.id"
      >
        <template #prepend>
          <v-avatar
            size="32"
            color="error"
            variant="tonal"
          >
            <span
              v-if="envelope.icon && !envelope.icon.startsWith('mdi-')"
              class="text-body-2"
            >
              {{ envelope.icon }}
            </span>
            <v-icon
              v-else
              size="18"
            >
              {{ getEnvelopeIcon(envelope) }}
            </v-icon>
          </v-avatar>
        </template>

        <v-list-item-title>{{ envelope.name }}</v-list-item-title>

        <template #append>
          <div class="d-flex align-center ga-2">
            <MoneyDisplay
              :amount="envelope.current_balance"
              size="small"
            />
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              @click="emit('cover-envelope', envelope.id)"
            >
              Cover
            </v-btn>
          </div>
        </template>
      </v-list-item>
    </v-list>
  </v-alert>
</template>
