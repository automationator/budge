import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import type { Transaction, Account } from '@/types'
import { useAccountsStore } from '@/stores/accounts'
import { usePayeesStore } from '@/stores/payees'
import { useEnvelopesStore } from '@/stores/envelopes'

export interface StatusChip {
  text: string
  color: string
}

export function useTransactionDisplay(transaction: MaybeRefOrGetter<Transaction>) {
  const accountsStore = useAccountsStore()
  const payeesStore = usePayeesStore()
  const envelopesStore = useEnvelopesStore()

  const account = computed<Account | undefined>(() =>
    accountsStore.getAccountById(toValue(transaction).account_id)
  )

  const payee = computed(() => {
    const txn = toValue(transaction)
    return txn.payee_id ? payeesStore.getPayeeById(txn.payee_id) : null
  })

  // Filter out the CC tracking envelope allocation for display purposes
  const userAllocations = computed(() => {
    const txn = toValue(transaction)
    const allocations = txn.allocations
    if (!allocations || allocations.length === 0) return []

    // Find if there's a CC envelope linked to this transaction's account
    const ccEnvelope = envelopesStore.envelopes.find(
      (e) => e.linked_account_id === txn.account_id
    )

    // Filter out the CC envelope allocation if it exists
    if (ccEnvelope) {
      return allocations.filter((a) => a.envelope_id !== ccEnvelope.id)
    }

    return allocations
  })

  // Returns envelope name for display, or null if unallocated (to hide it entirely)
  const envelopeDisplayText = computed<string | null>(() => {
    const allocations = userAllocations.value
    if (allocations.length === 0) return null

    // Check if all user allocations go to the Unallocated envelope - hide if so
    const isUnallocated = allocations.every((a) => {
      const envelope = envelopesStore.getEnvelopeById(a.envelope_id)
      return envelope?.is_unallocated === true
    })
    if (isUnallocated) return null

    if (allocations.length === 1) {
      const envelope = envelopesStore.getEnvelopeById(allocations[0]!.envelope_id)
      return envelope?.name || null
    }

    return 'Split'
  })

  const displayName = computed(() => {
    const txn = toValue(transaction)
    if (txn.transaction_type === 'transfer') {
      const linkedAccount = txn.linked_account_id
        ? accountsStore.getAccountById(txn.linked_account_id)
        : null
      if (linkedAccount) {
        return txn.amount < 0
          ? `Transfer to ${linkedAccount.name}`
          : `Transfer from ${linkedAccount.name}`
      }
      return 'Transfer'
    }
    if (txn.transaction_type === 'adjustment') {
      // Use memo if available (e.g., "Starting balance"), otherwise generic label
      return txn.memo || 'Balance Adjustment'
    }
    return payee.value?.name || 'Unknown Payee'
  })

  const formattedDate = computed(() => {
    const date = new Date(toValue(transaction).date + 'T00:00:00')
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  })

  const statusChip = computed<StatusChip | null>(() => {
    const txn = toValue(transaction)
    if (txn.status === 'scheduled') {
      return { text: 'Scheduled', color: 'warning' }
    }
    if (txn.status === 'skipped') {
      return { text: 'Skipped', color: 'grey' }
    }
    // Uncleared is now shown via icon, not chip
    return null
  })

  return {
    account,
    payee,
    userAllocations,
    envelopeDisplayText,
    displayName,
    formattedDate,
    statusChip,
  }
}
