import { ref } from 'vue'

// Global transaction dialog state (singleton)
export const showTransactionDialog = ref(false)
export const editingTransactionId = ref<string | null>(null)
export const preselectedAccountId = ref<string | null>(null)
export const preselectedEnvelopeId = ref<string | null>(null)

// Callback that components can register to be notified of changes
let onChangeCallback: (() => void) | null = null

export function openNewTransaction(accountId: string | null = null, envelopeId: string | null = null) {
  editingTransactionId.value = null
  preselectedAccountId.value = accountId
  preselectedEnvelopeId.value = envelopeId
  showTransactionDialog.value = true
}

export function openEditTransaction(transactionId: string) {
  editingTransactionId.value = transactionId
  preselectedAccountId.value = null
  preselectedEnvelopeId.value = null
  showTransactionDialog.value = true
}

export function closeTransactionDialog() {
  showTransactionDialog.value = false
}

export function setOnChangeCallback(callback: (() => void) | null) {
  onChangeCallback = callback
}

export function notifyTransactionChange() {
  if (onChangeCallback) {
    onChangeCallback()
  }
}
