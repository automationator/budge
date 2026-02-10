import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Transaction } from '@/types'
import { useAuthStore } from './auth'
import { useEnvelopesStore } from './envelopes'
import {
  listTransactions,
  getTransaction,
  createTransaction as apiCreateTransaction,
  createAdjustment as apiCreateAdjustment,
  updateTransaction as apiUpdateTransaction,
  deleteTransaction as apiDeleteTransaction,
  skipTransaction as apiSkipTransaction,
  createTransfer as apiCreateTransfer,
  updateTransfer as apiUpdateTransfer,
  deleteTransfer as apiDeleteTransfer,
  getUnallocatedCount as apiGetUnallocatedCount,
  type TransactionCreate,
  type AdjustmentCreate,
  type TransactionUpdate,
  type TransferCreate,
  type TransferUpdate,
  type ListTransactionsParams,
} from '@/api/transactions'

export const useTransactionsStore = defineStore('transactions', () => {
  // State
  const transactions = ref<Transaction[]>([])
  const cursor = ref<string | null>(null)
  const hasMore = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const unallocatedCount = ref(0)

  // Actions
  async function fetchTransactions(reset = false, params: ListTransactionsParams = {}) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    if (reset) {
      transactions.value = []
      cursor.value = null
      hasMore.value = false
    }

    try {
      loading.value = true
      error.value = null

      const response = await listTransactions(authStore.currentBudgetId, {
        ...params,
        cursor: cursor.value,
        limit: params.limit || 50,
      })

      if (reset) {
        transactions.value = response.items
      } else {
        transactions.value = [...transactions.value, ...response.items]
      }

      cursor.value = response.next_cursor
      hasMore.value = response.has_more
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch transactions'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTransaction(transactionId: string): Promise<Transaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const transaction = await getTransaction(authStore.currentBudgetId, transactionId)

      // Update in local cache
      const index = transactions.value.findIndex((t) => t.id === transactionId)
      if (index >= 0) {
        transactions.value[index] = transaction
      }

      return transaction
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTransaction(data: TransactionCreate): Promise<Transaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const transaction = await apiCreateTransaction(authStore.currentBudgetId, data)

      // Add to beginning of list (newest first)
      transactions.value = [transaction, ...transactions.value]

      return transaction
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createAdjustment(data: AdjustmentCreate): Promise<Transaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const transaction = await apiCreateAdjustment(authStore.currentBudgetId, data)

      // Add to beginning of list (newest first)
      transactions.value = [transaction, ...transactions.value]

      return transaction
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create adjustment'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateTransaction(
    transactionId: string,
    data: TransactionUpdate
  ): Promise<Transaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const transaction = await apiUpdateTransaction(
        authStore.currentBudgetId,
        transactionId,
        data
      )

      // Update in local cache
      const index = transactions.value.findIndex((t) => t.id === transactionId)
      if (index >= 0) {
        transactions.value[index] = transaction
      }

      return transaction
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTransaction(transactionId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeleteTransaction(authStore.currentBudgetId, transactionId)
      transactions.value = transactions.value.filter((t) => t.id !== transactionId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function skipTransaction(transactionId: string): Promise<Transaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const transaction = await apiSkipTransaction(authStore.currentBudgetId, transactionId)

      // Update in local cache
      const index = transactions.value.findIndex((t) => t.id === transactionId)
      if (index >= 0) {
        transactions.value[index] = transaction
      }

      return transaction
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to skip transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTransfer(data: TransferCreate) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const response = await apiCreateTransfer(authStore.currentBudgetId, data)

      // Add both transactions to list
      transactions.value = [
        response.source_transaction,
        response.destination_transaction,
        ...transactions.value,
      ]

      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create transfer'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateTransfer(transactionId: string, data: TransferUpdate) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const response = await apiUpdateTransfer(authStore.currentBudgetId, transactionId, data)

      // Update both transactions in cache
      const sourceId = response.source_transaction.id
      const destId = response.destination_transaction.id
      transactions.value = transactions.value.map((t) => {
        if (t.id === sourceId) return response.source_transaction
        if (t.id === destId) return response.destination_transaction
        return t
      })

      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update transfer'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTransfer(transactionId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null

      // Find the linked transaction before deleting
      const transaction = transactions.value.find((t) => t.id === transactionId)
      const linkedId = transaction?.linked_transaction_id

      await apiDeleteTransfer(authStore.currentBudgetId, transactionId)

      // Remove both transactions from cache
      transactions.value = transactions.value.filter(
        (t) => t.id !== transactionId && t.id !== linkedId
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete transfer'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getTransactionById(transactionId: string): Transaction | undefined {
    return transactions.value.find((t) => t.id === transactionId)
  }

  async function fetchUnallocatedCount(): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      const response = await apiGetUnallocatedCount(authStore.currentBudgetId)
      unallocatedCount.value = response.count
    } catch {
      // Silently fail - not critical
      unallocatedCount.value = 0
    }
  }

  async function fetchUnallocatedTransactions(limit = 5): Promise<Transaction[]> {
    const authStore = useAuthStore()
    const envelopesStore = useEnvelopesStore()
    if (!authStore.currentBudgetId) return []

    const unallocatedEnvelope = envelopesStore.unallocatedEnvelope
    if (!unallocatedEnvelope) return []

    try {
      // Use backend filtering to match count_unallocated_transactions logic:
      // - expenses_only: exclude income (expected in Unallocated for distribution)
      // - include_in_budget: only budget accounts (not tracking accounts)
      // - exclude_adjustments: exclude accounting entries (starting balances, etc.)
      const response = await listTransactions(authStore.currentBudgetId, {
        envelope_id: unallocatedEnvelope.id,
        limit: limit,
        include_in_budget: true,
        expenses_only: true,
        exclude_adjustments: true,
      })
      return response.items
    } catch {
      return []
    }
  }

  async function fetchRecentTransactions(limit = 5): Promise<Transaction[]> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return []

    try {
      const response = await listTransactions(authStore.currentBudgetId, {
        limit: limit,
      })
      return response.items
    } catch {
      return []
    }
  }

  function reset() {
    transactions.value = []
    cursor.value = null
    hasMore.value = false
    error.value = null
    unallocatedCount.value = 0
  }

  return {
    // State
    transactions,
    cursor,
    hasMore,
    loading,
    error,
    unallocatedCount,
    // Actions
    fetchTransactions,
    fetchTransaction,
    createTransaction,
    createAdjustment,
    updateTransaction,
    deleteTransaction,
    skipTransaction,
    createTransfer,
    updateTransfer,
    deleteTransfer,
    getTransactionById,
    fetchUnallocatedCount,
    fetchUnallocatedTransactions,
    fetchRecentTransactions,
    reset,
  }
})
