<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { formatMoney, getMoneyColor, parseMoney } from '@/utils/money'

const props = withDefaults(
  defineProps<{
    amount: number
    colored?: boolean
    editable?: boolean
    size?: 'small' | 'medium' | 'large'
  }>(),
  {
    colored: true,
    editable: true,
    size: 'medium',
  }
)

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

const emit = defineEmits<{
  save: [newAmount: number]
}>()

const isEditing = ref(false)
const editValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

const formattedAmount = computed(() => formatMoney(props.amount))
const colorClass = computed(() => (props.colored ? getMoneyColor(props.amount) : ''))

function startEditing() {
  if (!props.editable) return
  // Convert cents to dollars for editing
  editValue.value = (props.amount / 100).toFixed(2)
  isEditing.value = true
  nextTick(() => {
    inputRef.value?.focus()
    inputRef.value?.select()
  })
}

function cancelEditing() {
  isEditing.value = false
  editValue.value = ''
}

function saveValue() {
  const newAmount = parseMoney(editValue.value)
  if (newAmount !== props.amount) {
    emit('save', newAmount)
  }
  isEditing.value = false
  editValue.value = ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    cancelEditing()
  } else if (event.key === 'Enter') {
    saveValue()
  }
}

// Reset editing state if amount changes externally
watch(
  () => props.amount,
  () => {
    if (isEditing.value) {
      cancelEditing()
    }
  }
)
</script>

<template>
  <div class="inline-money-edit">
    <!-- Edit mode -->
    <div
      v-if="isEditing"
      class="edit-container"
    >
      <span class="prefix">$</span>
      <input
        ref="inputRef"
        v-model="editValue"
        type="text"
        inputmode="decimal"
        class="edit-input"
        @blur="saveValue"
        @keydown="handleKeydown"
      >
    </div>

    <!-- Display mode -->
    <span
      v-else
      :class="[colorClass, sizeClass, { editable: editable }]"
      class="display-value font-weight-medium"
      role="button"
      :tabindex="editable ? 0 : undefined"
      @click="startEditing"
      @keydown.enter="startEditing"
    >
      {{ formattedAmount }}
    </span>
  </div>
</template>

<style scoped>
.inline-money-edit {
  display: inline-flex;
  align-items: center;
}

.display-value {
  cursor: default;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background-color 0.15s;
}

.display-value.editable {
  cursor: pointer;
}

.display-value.editable:hover {
  background-color: rgba(0, 0, 0, 0.08);
}

.edit-container {
  display: inline-flex;
  align-items: center;
  background-color: rgb(var(--v-theme-surface-variant));
  border-radius: 4px;
  padding: 2px 4px;
}

.prefix {
  color: rgb(var(--v-theme-on-surface-variant));
  margin-right: 2px;
}

.edit-input {
  width: 80px;
  border: none;
  background: transparent;
  font-weight: 500;
  font-size: inherit;
  font-family: inherit;
  outline: none;
  color: rgb(var(--v-theme-on-surface-variant));
}

.edit-input:focus {
  outline: none;
}
</style>
