import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RecurringTransaction } from '@/types'
import { useAuthStore } from './auth'
import {
  listRecurringTransactions,
  getRecurringTransaction,
  createRecurringTransaction as apiCreate,
  updateRecurringTransaction as apiUpdate,
  deleteRecurringTransaction as apiDelete,
  type RecurringTransactionCreate,
  type RecurringTransactionUpdate,
} from '@/api/recurring'

export const useRecurringStore = defineStore('recurring', () => {
  // State
  const recurringTransactions = ref<RecurringTransaction[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const activeRecurring = computed(() =>
    recurringTransactions.value.filter((r) => r.is_active)
  )

  const upcomingRecurring = computed(() => {
    const now = new Date()
    return [...activeRecurring.value]
      .sort((a, b) => a.next_occurrence_date.localeCompare(b.next_occurrence_date))
      .filter((r) => new Date(r.next_occurrence_date) >= now)
  })

  const totalMonthlyExpenses = computed(() => {
    return activeRecurring.value
      .filter((r) => r.amount < 0)
      .reduce((sum, r) => {
        // Normalize to monthly amount
        let monthly = Math.abs(r.amount)
        switch (r.frequency_unit) {
          case 'days':
            monthly = monthly * 30 / r.frequency_value
            break
          case 'weeks':
            monthly = monthly * 4.33 / r.frequency_value
            break
          case 'months':
            monthly = monthly / r.frequency_value
            break
          case 'years':
            monthly = monthly / (12 * r.frequency_value)
            break
        }
        return sum + Math.round(monthly)
      }, 0)
  })

  const totalMonthlyIncome = computed(() => {
    return activeRecurring.value
      .filter((r) => r.amount > 0 && !r.destination_account_id)
      .reduce((sum, r) => {
        // Normalize to monthly amount
        let monthly = r.amount
        switch (r.frequency_unit) {
          case 'days':
            monthly = monthly * 30 / r.frequency_value
            break
          case 'weeks':
            monthly = monthly * 4.33 / r.frequency_value
            break
          case 'months':
            monthly = monthly / r.frequency_value
            break
          case 'years':
            monthly = monthly / (12 * r.frequency_value)
            break
        }
        return sum + Math.round(monthly)
      }, 0)
  })

  // Actions
  async function fetchRecurringTransactions(includeInactive = false) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      recurringTransactions.value = await listRecurringTransactions(
        authStore.currentBudgetId,
        includeInactive
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch recurring transactions'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRecurringTransaction(id: string): Promise<RecurringTransaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const recurring = await getRecurringTransaction(authStore.currentBudgetId, id)

      // Update in cache
      const index = recurringTransactions.value.findIndex((r) => r.id === id)
      if (index >= 0) {
        recurringTransactions.value[index] = recurring
      } else {
        recurringTransactions.value.push(recurring)
      }

      return recurring
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch recurring transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createRecurringTransaction(
    data: RecurringTransactionCreate
  ): Promise<RecurringTransaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const recurring = await apiCreate(authStore.currentBudgetId, data)
      recurringTransactions.value.push(recurring)
      return recurring
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create recurring transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateRecurringTransaction(
    id: string,
    data: RecurringTransactionUpdate,
    propagateToFuture = true
  ): Promise<RecurringTransaction> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const recurring = await apiUpdate(authStore.currentBudgetId, id, data, propagateToFuture)

      const index = recurringTransactions.value.findIndex((r) => r.id === id)
      if (index >= 0) {
        recurringTransactions.value[index] = recurring
      }

      return recurring
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update recurring transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteRecurringTransaction(
    id: string,
    deleteScheduled = true
  ): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDelete(authStore.currentBudgetId, id, deleteScheduled)
      recurringTransactions.value = recurringTransactions.value.filter((r) => r.id !== id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete recurring transaction'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getById(id: string): RecurringTransaction | undefined {
    return recurringTransactions.value.find((r) => r.id === id)
  }

  function reset() {
    recurringTransactions.value = []
    error.value = null
  }

  return {
    // State
    recurringTransactions,
    loading,
    error,
    // Getters
    activeRecurring,
    upcomingRecurring,
    totalMonthlyExpenses,
    totalMonthlyIncome,
    // Actions
    fetchRecurringTransactions,
    fetchRecurringTransaction,
    createRecurringTransaction,
    updateRecurringTransaction,
    deleteRecurringTransaction,
    getById,
    reset,
  }
})
