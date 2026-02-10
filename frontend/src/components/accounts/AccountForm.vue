<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Account, AccountType } from '@/types'

const props = defineProps<{
  account?: Account | null
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [data: FormData]
  cancel: []
}>()

export interface FormData {
  name: string
  account_type: AccountType
  icon: string | null
  description: string | null
  include_in_budget: boolean
  is_active: boolean
  starting_balance?: number | null // In cents, only for new accounts
}

const accountTypes: { value: AccountType; title: string; icon: string }[] = [
  { value: 'checking', title: 'Checking', icon: 'mdi-bank' },
  { value: 'savings', title: 'Savings', icon: 'mdi-piggy-bank' },
  { value: 'credit_card', title: 'Credit Card', icon: 'mdi-credit-card' },
  { value: 'cash', title: 'Cash', icon: 'mdi-cash' },
  { value: 'investment', title: 'Investment', icon: 'mdi-chart-line' },
  { value: 'loan', title: 'Loan', icon: 'mdi-hand-coin' },
  { value: 'other', title: 'Other', icon: 'mdi-wallet' },
]

const commonIcons = [
  { value: '🏦', label: 'Bank' },
  { value: '🐷', label: 'Savings' },
  { value: '💳', label: 'Card' },
  { value: '💵', label: 'Cash' },
  { value: '👛', label: 'Wallet' },
  { value: '📈', label: 'Investment' },
  { value: '🏠', label: 'Home' },
  { value: '🚗', label: 'Car' },
  { value: '🍔', label: 'Food' },
  { value: '🏥', label: 'Medical' },
  { value: '🎓', label: 'School' },
  { value: '💼', label: 'Work' },
  { value: '🎁', label: 'Gifts' },
  { value: '❤️', label: 'Personal' },
]

const name = ref('')
const accountType = ref<AccountType>('checking')
const description = ref('')
const includeInBudget = ref(true)
const isActive = ref(true)
const startingBalance = ref('')
const selectedIcon = ref<string | null>(null)
const customIconInput = ref('')

const isEditing = computed(() => !!props.account)

// Reset form when account changes
watch(
  () => props.account,
  (account) => {
    if (account) {
      name.value = account.name
      accountType.value = account.account_type
      description.value = account.description || ''
      includeInBudget.value = account.include_in_budget
      isActive.value = account.is_active
      startingBalance.value = ''
      // Check if icon is in common icons list or is a custom icon
      if (account.icon) {
        const isCommonIcon = commonIcons.some((i) => i.value === account.icon)
        if (isCommonIcon) {
          selectedIcon.value = account.icon
          customIconInput.value = ''
        } else {
          selectedIcon.value = null
          customIconInput.value = account.icon
        }
      } else {
        selectedIcon.value = null
        customIconInput.value = ''
      }
    } else {
      name.value = ''
      accountType.value = 'checking'
      description.value = ''
      includeInBudget.value = true
      isActive.value = true
      startingBalance.value = ''
      selectedIcon.value = null
      customIconInput.value = ''
    }
  },
  { immediate: true }
)

const rules = {
  required: (v: string) => !!v || 'Required',
}

const formValid = ref(false)

// Compute the final icon value: custom input takes priority, then selected icon, then null
const finalIcon = computed(() => {
  const trimmedCustom = customIconInput.value.trim()
  if (trimmedCustom) {
    return trimmedCustom
  }
  return selectedIcon.value
})

function clearIcon() {
  selectedIcon.value = null
  customIconInput.value = ''
}

function handleSubmit() {
  if (!name.value.trim()) return

  // Parse starting balance if provided (convert to cents)
  let startingBalanceCents: number | null = null
  if (startingBalance.value.trim()) {
    const parsed = parseFloat(startingBalance.value)
    if (!isNaN(parsed)) {
      startingBalanceCents = Math.round(parsed * 100)
    }
  }

  emit('submit', {
    name: name.value.trim(),
    account_type: accountType.value,
    icon: finalIcon.value,
    description: description.value.trim() || null,
    include_in_budget: includeInBudget.value,
    is_active: isActive.value,
    starting_balance: startingBalanceCents,
  })
}
</script>

<template>
  <v-form
    v-model="formValid"
    @submit.prevent="handleSubmit"
  >
    <v-text-field
      v-model="name"
      label="Account Name"
      :rules="[rules.required]"
      autofocus
    />

    <v-select
      v-model="accountType"
      label="Account Type"
      :items="accountTypes"
      item-value="value"
      item-title="title"
      class="mt-4"
    >
      <template #item="{ props: itemProps, item }">
        <v-list-item v-bind="itemProps">
          <template #prepend>
            <v-icon>{{ item.raw.icon }}</v-icon>
          </template>
        </v-list-item>
      </template>
    </v-select>

    <!-- Icon Picker -->
    <div class="mt-4">
      <div class="text-subtitle-2 mb-2">
        Icon
      </div>
      <v-chip-group
        v-model="selectedIcon"
        column
        selected-class="text-primary"
      >
        <v-chip
          v-for="icon in commonIcons"
          :key="icon.value"
          :value="icon.value"
          filter
          size="small"
          data-testid="icon-chip"
        >
          <span class="mr-1">{{ icon.value }}</span>
          {{ icon.label }}
        </v-chip>
      </v-chip-group>

      <v-text-field
        v-model="customIconInput"
        label="Custom emoji"
        hint="Enter any emoji"
        persistent-hint
        density="compact"
        class="mt-2"
        data-testid="custom-icon-input"
      />

      <v-btn
        v-if="selectedIcon || customIconInput"
        variant="text"
        size="small"
        class="mt-1"
        data-testid="use-default-icon-button"
        @click="clearIcon"
      >
        Use default icon
      </v-btn>
    </div>

    <v-textarea
      v-model="description"
      label="Description (optional)"
      rows="2"
      class="mt-4"
    />

    <v-text-field
      v-if="!isEditing"
      v-model="startingBalance"
      label="Starting Balance (optional)"
      type="number"
      step="0.01"
      prefix="$"
      hint="Set an initial balance for this account"
      persistent-hint
      class="mt-4"
    />

    <v-switch
      v-model="includeInBudget"
      label="Include in budget"
      color="primary"
      hint="Include this account's balance in your budget totals"
      persistent-hint
      class="mt-4"
    />

    <v-switch
      v-if="isEditing"
      v-model="isActive"
      label="Active"
      color="primary"
      hint="Inactive accounts are hidden from the main view"
      persistent-hint
      class="mt-2"
    />

    <div class="d-flex justify-end gap-2 mt-6">
      <v-btn
        variant="text"
        @click="emit('cancel')"
      >
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        :loading="loading"
        :disabled="!formValid"
        @click="handleSubmit"
      >
        {{ isEditing ? 'Save' : 'Create' }}
      </v-btn>
    </div>
  </v-form>
</template>
