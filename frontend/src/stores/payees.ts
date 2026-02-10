import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Payee } from '@/types'
import { useAuthStore } from './auth'
import {
  listPayees,
  createPayee as apiCreatePayee,
  updatePayee as apiUpdatePayee,
  deletePayee as apiDeletePayee,
  type PayeeCreate,
  type PayeeUpdate,
} from '@/api/payees'

export const usePayeesStore = defineStore('payees', () => {
  // State
  const payees = ref<Payee[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const sortedPayees = computed(() =>
    [...payees.value].sort((a, b) => a.name.localeCompare(b.name))
  )

  // Actions
  async function fetchPayees() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      payees.value = await listPayees(authStore.currentBudgetId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch payees'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createPayee(data: PayeeCreate): Promise<Payee> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const payee = await apiCreatePayee(authStore.currentBudgetId, data)
      payees.value.push(payee)
      return payee
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create payee'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updatePayee(payeeId: string, data: PayeeUpdate): Promise<Payee> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const payee = await apiUpdatePayee(authStore.currentBudgetId, payeeId, data)

      const index = payees.value.findIndex((p) => p.id === payeeId)
      if (index >= 0) {
        payees.value[index] = payee
      }

      return payee
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update payee'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deletePayee(payeeId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeletePayee(authStore.currentBudgetId, payeeId)
      payees.value = payees.value.filter((p) => p.id !== payeeId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete payee'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getPayeeById(payeeId: string): Payee | undefined {
    return payees.value.find((p) => p.id === payeeId)
  }

  function getDefaultEnvelopeId(payeeId: string): string | null {
    const payee = getPayeeById(payeeId)
    return payee?.default_envelope_id ?? null
  }

  function reset() {
    payees.value = []
    error.value = null
  }

  return {
    // State
    payees,
    loading,
    error,
    // Getters
    sortedPayees,
    // Actions
    fetchPayees,
    createPayee,
    updatePayee,
    deletePayee,
    getPayeeById,
    getDefaultEnvelopeId,
    reset,
  }
})
