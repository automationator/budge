import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AllocationRule } from '@/types'
import { useAuthStore } from './auth'
import {
  listAllocationRules,
  getAllocationRule,
  createAllocationRule as apiCreate,
  updateAllocationRule as apiUpdate,
  deleteAllocationRule as apiDelete,
  previewAllocationRules as apiPreview,
  type AllocationRuleCreate,
  type AllocationRuleUpdate,
  type RulePreviewResponse,
} from '@/api/allocationRules'

export const useAllocationRulesStore = defineStore('allocationRules', () => {
  // State
  const allocationRules = ref<AllocationRule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const sortedRules = computed(() =>
    [...allocationRules.value].sort((a, b) => {
      const aIsCap = a.rule_type === 'period_cap' ? 1 : 0
      const bIsCap = b.rule_type === 'period_cap' ? 1 : 0
      if (aIsCap !== bIsCap) return aIsCap - bIsCap
      return a.priority - b.priority
    })
  )

  const activeRules = computed(() =>
    sortedRules.value.filter((r) => r.is_active)
  )

  const rulesByEnvelope = computed(() => {
    const grouped: Record<string, AllocationRule[]> = {}
    for (const rule of sortedRules.value) {
      const list = grouped[rule.envelope_id] ?? []
      list.push(rule)
      grouped[rule.envelope_id] = list
    }
    return grouped
  })

  // Actions
  async function fetchAllocationRules(activeOnly = false) {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      allocationRules.value = await listAllocationRules(
        authStore.currentBudgetId,
        activeOnly
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch allocation rules'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchAllocationRule(id: string): Promise<AllocationRule> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const rule = await getAllocationRule(authStore.currentBudgetId, id)

      // Update in cache
      const index = allocationRules.value.findIndex((r) => r.id === id)
      if (index >= 0) {
        allocationRules.value[index] = rule
      } else {
        allocationRules.value.push(rule)
      }

      return rule
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch allocation rule'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createAllocationRule(data: AllocationRuleCreate): Promise<AllocationRule> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const rule = await apiCreate(authStore.currentBudgetId, data)
      allocationRules.value.push(rule)
      return rule
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create allocation rule'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateAllocationRule(
    id: string,
    data: AllocationRuleUpdate
  ): Promise<AllocationRule> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const rule = await apiUpdate(authStore.currentBudgetId, id, data)

      const index = allocationRules.value.findIndex((r) => r.id === id)
      if (index >= 0) {
        allocationRules.value[index] = rule
      }

      return rule
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update allocation rule'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteAllocationRule(id: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDelete(authStore.currentBudgetId, id)
      allocationRules.value = allocationRules.value.filter((r) => r.id !== id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete allocation rule'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function previewRules(amount: number): Promise<RulePreviewResponse> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    // Note: Preview does not update store state
    return await apiPreview(authStore.currentBudgetId, { amount })
  }

  function getById(id: string): AllocationRule | undefined {
    return allocationRules.value.find((r) => r.id === id)
  }

  function envelopeHasPeriodCap(envelopeId: string, excludeRuleId?: string): boolean {
    return allocationRules.value.some(
      (r) =>
        r.envelope_id === envelopeId &&
        r.rule_type === 'period_cap' &&
        r.id !== excludeRuleId
    )
  }

  function reset() {
    allocationRules.value = []
    error.value = null
  }

  return {
    // State
    allocationRules,
    loading,
    error,
    // Getters
    sortedRules,
    activeRules,
    rulesByEnvelope,
    // Actions
    fetchAllocationRules,
    fetchAllocationRule,
    createAllocationRule,
    updateAllocationRule,
    deleteAllocationRule,
    previewRules,
    getById,
    envelopeHasPeriodCap,
    reset,
  }
})
