<script setup lang="ts">
import { computed } from 'vue'
import type { EnvelopeBudgetItem } from '@/api/envelopes'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import InlineMoneyEdit from '@/components/common/InlineMoneyEdit.vue'
import EnvelopeRuleIcons from '@/components/envelopes/EnvelopeRuleIcons.vue'

const props = defineProps<{
  item: EnvelopeBudgetItem
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
  activityClick: []
  balanceSave: [newBalance: number]
}>()

const isCreditCard = computed(() => props.item.linked_account_id !== null)
</script>

<template>
  <v-list-item
    class="budget-row py-2"
    :class="{ 'credit-card': isCreditCard }"
    @click="emit('click')"
  >
    <template #prepend>
      <v-avatar
        color="primary"
        variant="tonal"
        size="36"
        class="mr-3"
      >
        <!-- Show emoji if set (not an MDI icon), otherwise show MDI icon -->
        <span
          v-if="item.icon && !item.icon.startsWith('mdi-')"
          class="emoji-icon"
        >
          {{ item.icon }}
        </span>
        <v-icon
          v-else
          size="small"
        >
          {{ item.icon || (isCreditCard ? 'mdi-credit-card' : 'mdi-wallet') }}
        </v-icon>
      </v-avatar>
    </template>

    <v-list-item-title class="font-weight-medium d-flex align-center gap-3 envelope-name">
      {{ item.envelope_name }}
      <EnvelopeRuleIcons :envelope-id="item.envelope_id" />
    </v-list-item-title>

    <template #append>
      <div class="d-flex align-center budget-columns">
        <!-- Edit mode: show reorder buttons instead of columns -->
        <template v-if="editMode">
          <v-btn
            icon="mdi-chevron-up"
            size="x-small"
            variant="text"
            :disabled="isFirst || reorderLoading"
            @click.stop="emit('moveUp')"
          />
          <v-btn
            icon="mdi-chevron-down"
            size="x-small"
            variant="text"
            :disabled="isLast || reorderLoading"
            @click.stop="emit('moveDown')"
          />
        </template>

        <!-- Normal mode: show budget columns -->
        <template v-else>
          <!-- Activity Column (clickable) -->
          <div
            class="budget-column activity-column text-right"
            role="button"
            tabindex="0"
            @click.stop="emit('activityClick')"
            @keydown.enter.stop="emit('activityClick')"
          >
            <MoneyDisplay
              :amount="item.activity"
              size="small"
              class="activity-value"
            />
          </div>

          <!-- Balance Column (inline edit) -->
          <div
            class="budget-column balance-column text-right"
            @click.stop
          >
            <InlineMoneyEdit
              :amount="item.balance"
              :colored="true"
              :editable="!isCreditCard"
              size="small"
              @save="(val: number) => emit('balanceSave', val)"
            />
          </div>

          <!-- Action Buttons -->
          <div class="action-buttons d-flex align-center gap-1 ml-2">
            <v-tooltip
              text="Transfer"
              location="top"
            >
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  icon="mdi-swap-horizontal"
                  size="x-small"
                  variant="text"
                  @click.stop="emit('transfer')"
                />
              </template>
            </v-tooltip>
            <v-tooltip
              v-if="!isCreditCard"
              text="Add Transaction"
              location="top"
            >
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  icon="mdi-plus"
                  size="x-small"
                  variant="text"
                  @click.stop="emit('addTransaction')"
                />
              </template>
            </v-tooltip>
          </div>
        </template>
      </div>
    </template>
  </v-list-item>
</template>

<style scoped>
.budget-row {
  min-height: 48px;
}

.envelope-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.budget-columns {
  gap: 0;
}

.budget-column {
  width: 100px;
  min-width: 100px;
  padding: 0 8px;
  box-sizing: border-box;
}

.activity-column {
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.15s;
}

.activity-column:hover {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.activity-value {
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 2px;
}

.action-buttons {
  width: 60px;
  min-width: 60px;
  justify-content: flex-end;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.budget-row:hover .action-buttons {
  opacity: 1;
}

/* Emoji icon styling */
.emoji-icon {
  font-size: 18px;
  line-height: 1;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .budget-column {
    width: 80px;
    min-width: 80px;
    padding: 0 2px;
    white-space: nowrap;
  }

  .activity-column {
    display: none;
  }

  .action-buttons {
    display: none !important;
  }

  /* Reduce avatar size and margin on mobile to save space */
  .budget-row :deep(.v-avatar) {
    width: 24px !important;
    height: 24px !important;
    min-width: 24px !important;
    margin-right: 6px !important;
  }

  .budget-row :deep(.v-avatar .v-icon) {
    font-size: 12px !important;
  }

  .emoji-icon {
    font-size: 14px !important;
  }
}
</style>
