import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia } from 'pinia'
import { useAllocationRulesStore } from '@/stores/allocationRules'
import { useAuthStore } from '@/stores/auth'
import { createTestPinia, factories } from '@test/setup'

// Mock the allocation rules API
vi.mock('@/api/allocationRules', () => ({
  listAllocationRules: vi.fn(),
  getAllocationRule: vi.fn(),
  createAllocationRule: vi.fn(),
  updateAllocationRule: vi.fn(),
  deleteAllocationRule: vi.fn(),
  previewAllocationRules: vi.fn(),
}))

// Mock the auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}))

import * as allocationRulesApi from '@/api/allocationRules'

describe('useAllocationRulesStore', () => {
  const mockAuthStore = {
    currentBudgetId: 'budget-1',
  }

  beforeEach(() => {
    setActivePinia(createTestPinia())
    vi.clearAllMocks()

    // Set up auth store mock
    ;(useAuthStore as Mock).mockReturnValue(mockAuthStore)

    // Set up default API mock implementations
    ;(allocationRulesApi.listAllocationRules as Mock).mockResolvedValue([
      factories.allocationRule(),
      factories.allocationRule({
        id: 'rule-2',
        priority: 1,
        rule_type: 'percentage',
        amount: 1000,
      }),
    ])
    ;(allocationRulesApi.getAllocationRule as Mock).mockResolvedValue(
      factories.allocationRule()
    )
    ;(allocationRulesApi.createAllocationRule as Mock).mockImplementation(
      async (_teamId, data) => factories.allocationRule({ ...data, id: 'new-rule-id' })
    )
    ;(allocationRulesApi.updateAllocationRule as Mock).mockImplementation(
      async (_teamId, ruleId, data) => factories.allocationRule({ ...data, id: ruleId })
    )
    ;(allocationRulesApi.deleteAllocationRule as Mock).mockResolvedValue(undefined)
    ;(allocationRulesApi.previewAllocationRules as Mock).mockResolvedValue(
      factories.rulePreviewResponse()
    )
  })

  describe('initial state', () => {
    it('has correct initial values', () => {
      const store = useAllocationRulesStore()

      expect(store.allocationRules).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('sortedRules returns rules sorted by priority', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [
        factories.allocationRule({ id: 'a', priority: 2 }),
        factories.allocationRule({ id: 'b', priority: 0 }),
        factories.allocationRule({ id: 'c', priority: 1 }),
      ]

      expect(store.sortedRules[0]!.id).toBe('b')
      expect(store.sortedRules[1]!.id).toBe('c')
      expect(store.sortedRules[2]!.id).toBe('a')
    })

    it('activeRules filters to active rules only', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [
        factories.allocationRule({ id: 'a', is_active: true }),
        factories.allocationRule({ id: 'b', is_active: false }),
        factories.allocationRule({ id: 'c', is_active: true }),
      ]

      expect(store.activeRules.length).toBe(2)
      expect(store.activeRules.every((r) => r.is_active)).toBe(true)
    })

    it('rulesByEnvelope groups rules by envelope', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [
        factories.allocationRule({ id: 'a', envelope_id: 'env-1' }),
        factories.allocationRule({ id: 'b', envelope_id: 'env-2' }),
        factories.allocationRule({ id: 'c', envelope_id: 'env-1' }),
      ]

      expect(store.rulesByEnvelope['env-1']!.length).toBe(2)
      expect(store.rulesByEnvelope['env-2']!.length).toBe(1)
    })
  })

  describe('fetchAllocationRules', () => {
    it('does nothing when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await store.fetchAllocationRules()

      expect(store.allocationRules).toEqual([])
      expect(allocationRulesApi.listAllocationRules).not.toHaveBeenCalled()
    })

    it('fetches rules for current budget', async () => {
      const store = useAllocationRulesStore()
      await store.fetchAllocationRules()

      expect(allocationRulesApi.listAllocationRules).toHaveBeenCalledWith('budget-1', false)
      expect(store.allocationRules.length).toBe(2)
      expect(store.loading).toBe(false)
    })

    it('passes activeOnly parameter', async () => {
      const store = useAllocationRulesStore()
      await store.fetchAllocationRules(true)

      expect(allocationRulesApi.listAllocationRules).toHaveBeenCalledWith('budget-1', true)
    })

    it('sets loading state during fetch', async () => {
      const store = useAllocationRulesStore()

      const fetchPromise = store.fetchAllocationRules()
      expect(store.loading).toBe(true)

      await fetchPromise
      expect(store.loading).toBe(false)
    })

    it('sets error on fetch failure', async () => {
      ;(allocationRulesApi.listAllocationRules as Mock).mockRejectedValue(
        new Error('Network error')
      )

      const store = useAllocationRulesStore()
      await expect(store.fetchAllocationRules()).rejects.toThrow()

      expect(store.error).toBeTruthy()
    })
  })

  describe('fetchAllocationRule', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await expect(store.fetchAllocationRule('rule-1')).rejects.toThrow('No budget selected')
    })

    it('fetches single rule and updates cache', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [factories.allocationRule({ name: 'Old Name' })]

      const updatedRule = factories.allocationRule({ name: 'Updated Name' })
      ;(allocationRulesApi.getAllocationRule as Mock).mockResolvedValue(updatedRule)

      const result = await store.fetchAllocationRule('rule-1')

      expect(result.name).toBe('Updated Name')
      expect(store.allocationRules[0]!.name).toBe('Updated Name')
    })

    it('adds rule to cache if not found', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = []

      const newRule = factories.allocationRule()
      ;(allocationRulesApi.getAllocationRule as Mock).mockResolvedValue(newRule)

      await store.fetchAllocationRule('rule-1')

      expect(store.allocationRules.length).toBe(1)
    })
  })

  describe('createAllocationRule', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await expect(
        store.createAllocationRule({
          envelope_id: 'env-1',
          priority: 0,
          rule_type: 'fixed',
        })
      ).rejects.toThrow('No budget selected')
    })

    it('creates rule and adds to state', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = []

      const rule = await store.createAllocationRule({
        envelope_id: 'env-1',
        priority: 0,
        rule_type: 'fixed',
        amount: 10000,
        name: 'New Rule',
      })

      expect(rule.name).toBe('New Rule')
      expect(store.allocationRules.length).toBe(1)
      expect(store.allocationRules[0]!.name).toBe('New Rule')
    })

    it('calls API with correct parameters', async () => {
      const store = useAllocationRulesStore()

      await store.createAllocationRule({
        envelope_id: 'env-1',
        priority: 0,
        rule_type: 'percentage',
        amount: 1000,
      })

      expect(allocationRulesApi.createAllocationRule).toHaveBeenCalledWith('budget-1', {
        envelope_id: 'env-1',
        priority: 0,
        rule_type: 'percentage',
        amount: 1000,
      })
    })
  })

  describe('updateAllocationRule', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await expect(
        store.updateAllocationRule('rule-1', { name: 'Updated' })
      ).rejects.toThrow('No budget selected')
    })

    it('updates rule in local cache', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [factories.allocationRule({ name: 'Original' })]

      ;(allocationRulesApi.updateAllocationRule as Mock).mockResolvedValue(
        factories.allocationRule({ name: 'Updated' })
      )

      await store.updateAllocationRule('rule-1', { name: 'Updated' })

      expect(store.allocationRules[0]!.name).toBe('Updated')
    })

    it('returns updated rule', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [factories.allocationRule()]

      ;(allocationRulesApi.updateAllocationRule as Mock).mockResolvedValue(
        factories.allocationRule({ name: 'Updated' })
      )

      const result = await store.updateAllocationRule('rule-1', { name: 'Updated' })

      expect(result.name).toBe('Updated')
    })
  })

  describe('deleteAllocationRule', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await expect(store.deleteAllocationRule('rule-1')).rejects.toThrow('No budget selected')
    })

    it('removes rule from state', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [
        factories.allocationRule({ id: 'rule-1' }),
        factories.allocationRule({ id: 'rule-2' }),
      ]

      await store.deleteAllocationRule('rule-1')

      expect(store.allocationRules.length).toBe(1)
      expect(store.allocationRules[0]!.id).toBe('rule-2')
    })
  })

  describe('previewRules', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAllocationRulesStore()
      await expect(store.previewRules(100000)).rejects.toThrow('No budget selected')
    })

    it('calls preview API and returns result', async () => {
      const store = useAllocationRulesStore()

      const result = await store.previewRules(100000)

      expect(allocationRulesApi.previewAllocationRules).toHaveBeenCalledWith('budget-1', {
        amount: 100000,
      })
      expect(result.income_amount).toBe(100000)
      expect(result.allocations.length).toBeGreaterThan(0)
    })

    it('does not modify store state', async () => {
      const store = useAllocationRulesStore()
      store.allocationRules = []

      await store.previewRules(100000)

      expect(store.allocationRules).toEqual([])
    })
  })

  describe('getById', () => {
    it('returns rule by id', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [
        factories.allocationRule({ id: 'test-id', name: 'Test Rule' }),
      ]

      const rule = store.getById('test-id')

      expect(rule?.name).toBe('Test Rule')
    })

    it('returns undefined for unknown id', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = []

      expect(store.getById('unknown')).toBeUndefined()
    })
  })

  describe('reset', () => {
    it('clears all state', () => {
      const store = useAllocationRulesStore()
      store.allocationRules = [factories.allocationRule()]
      store.error = 'Some error'

      store.reset()

      expect(store.allocationRules).toEqual([])
      expect(store.error).toBeNull()
    })
  })
})
