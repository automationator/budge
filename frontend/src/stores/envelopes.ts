import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Envelope, EnvelopeGroup } from '@/types'
import { useAuthStore } from './auth'
import {
  listEnvelopes,
  listEnvelopeGroups,
  getEnvelope,
  getEnvelopeSummary,
  getEnvelopeBudgetSummary,
  getEnvelopeActivity,
  createEnvelope as apiCreateEnvelope,
  updateEnvelope as apiUpdateEnvelope,
  deleteEnvelope as apiDeleteEnvelope,
  createEnvelopeGroup as apiCreateEnvelopeGroup,
  updateEnvelopeGroup as apiUpdateEnvelopeGroup,
  deleteEnvelopeGroup as apiDeleteEnvelopeGroup,
  transferBetweenEnvelopes as apiTransfer,
  type EnvelopeCreate,
  type EnvelopeUpdate,
  type EnvelopeGroupCreate,
  type EnvelopeGroupUpdate,
  type EnvelopeBudgetSummaryResponse,
  type EnvelopeActivityResponse,
} from '@/api/envelopes'

// Date range helper functions
function formatDate(date: Date): string {
  return date.toISOString().split('T')[0]!
}

function getFirstDayOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function getFirstDayOfPreviousMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() - 1, 1)
}

function getLastDayOfPreviousMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 0)
}

function getFirstDayOfNMonthsAgo(date: Date, n: number): Date {
  return new Date(date.getFullYear(), date.getMonth() - n, 1)
}

function getFirstDayOfYear(date: Date): Date {
  return new Date(date.getFullYear(), 0, 1)
}

export type DateRangePreset =
  | 'this_month'
  | 'last_month'
  | 'last_3_months'
  | 'year_to_date'
  | 'custom'

export interface DateRange {
  startDate: string
  endDate: string
  preset: DateRangePreset
}

export const useEnvelopesStore = defineStore('envelopes', () => {
  // State
  const envelopes = ref<Envelope[]>([])
  const envelopeGroups = ref<EnvelopeGroup[]>([])
  const unfundedCcDebt = ref<number>(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isEditMode = ref(false)
  const reorderLoading = ref(false)

  // Date range state for budget view (default: current month)
  const today = new Date()
  const dateRange = ref<DateRange>({
    startDate: formatDate(getFirstDayOfMonth(today)),
    endDate: formatDate(today), // Today, not end of month
    preset: 'this_month',
  })

  // Budget summary state
  const budgetSummary = ref<EnvelopeBudgetSummaryResponse | null>(null)
  const budgetSummaryLoading = ref(false)

  // Getters
  const totalBudgeted = computed(() =>
    envelopes.value
      .filter((e) => e.is_active && !e.is_unallocated)
      .reduce((sum, e) => sum + e.current_balance, 0)
  )

  const unallocatedBalance = computed(() => {
    const unallocated = envelopes.value.find((e) => e.is_unallocated)
    return unallocated?.current_balance ?? 0
  })

  const unallocatedEnvelope = computed(() =>
    envelopes.value.find((e) => e.is_unallocated)
  )

  const activeEnvelopes = computed(() =>
    envelopes.value.filter((e) => e.is_active && !e.is_unallocated).sort((a, b) => a.sort_order - b.sort_order)
  )

  const overspentEnvelopes = computed(() =>
    envelopes.value.filter(
      (e) => e.is_active && !e.is_unallocated && e.current_balance < 0
    )
  )

  const creditCardEnvelopes = computed(() =>
    envelopes.value
      .filter((e) => e.linked_account_id !== null && e.is_active)
      .sort((a, b) => a.name.localeCompare(b.name))
  )

  const starredEnvelopes = computed(() =>
    envelopes.value
      .filter((e) => e.is_starred && e.is_active && !e.is_unallocated)
      .sort((a, b) => a.name.localeCompare(b.name))
  )

  const envelopesByGroup = computed(() => {
    const grouped: Record<string, Envelope[]> = { ungrouped: [] }

    // Initialize groups
    for (const group of envelopeGroups.value) {
      grouped[group.id] = []
    }

    // Assign envelopes to groups
    for (const envelope of activeEnvelopes.value) {
      const groupId = envelope.envelope_group_id
      if (groupId && grouped[groupId]) {
        grouped[groupId]!.push(envelope)
      } else {
        grouped['ungrouped']!.push(envelope)
      }
    }

    return grouped
  })

  // Actions
  async function fetchEnvelopes() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      const [envelopesData, groupsData, summaryData] = await Promise.all([
        listEnvelopes(authStore.currentBudgetId),
        listEnvelopeGroups(authStore.currentBudgetId),
        getEnvelopeSummary(authStore.currentBudgetId),
      ])
      envelopes.value = envelopesData
      envelopeGroups.value = groupsData
      unfundedCcDebt.value = summaryData.unfunded_cc_debt
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch envelopes'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchEnvelopeGroups() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      envelopeGroups.value = await listEnvelopeGroups(authStore.currentBudgetId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch envelope groups'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchEnvelope(envelopeId: string): Promise<Envelope> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const envelope = await getEnvelope(authStore.currentBudgetId, envelopeId)

      // Update in local cache
      const index = envelopes.value.findIndex((e) => e.id === envelopeId)
      if (index >= 0) {
        envelopes.value[index] = envelope
      } else {
        envelopes.value.push(envelope)
      }

      return envelope
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch envelope'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createEnvelope(data: EnvelopeCreate): Promise<Envelope> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const envelope = await apiCreateEnvelope(authStore.currentBudgetId, data)
      envelopes.value.push(envelope)
      return envelope
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create envelope'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEnvelope(envelopeId: string, data: EnvelopeUpdate): Promise<Envelope> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const envelope = await apiUpdateEnvelope(authStore.currentBudgetId, envelopeId, data)

      const index = envelopes.value.findIndex((e) => e.id === envelopeId)
      if (index >= 0) {
        envelopes.value[index] = envelope
      }

      return envelope
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update envelope'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteEnvelope(envelopeId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeleteEnvelope(authStore.currentBudgetId, envelopeId)
      envelopes.value = envelopes.value.filter((e) => e.id !== envelopeId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete envelope'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createEnvelopeGroup(data: EnvelopeGroupCreate): Promise<EnvelopeGroup> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const group = await apiCreateEnvelopeGroup(authStore.currentBudgetId, data)
      envelopeGroups.value.push(group)
      return group
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create group'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEnvelopeGroup(
    groupId: string,
    data: EnvelopeGroupUpdate
  ): Promise<EnvelopeGroup> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const group = await apiUpdateEnvelopeGroup(authStore.currentBudgetId, groupId, data)

      const index = envelopeGroups.value.findIndex((g) => g.id === groupId)
      if (index >= 0) {
        envelopeGroups.value[index] = group
      }

      return group
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update group'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteEnvelopeGroup(groupId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeleteEnvelopeGroup(authStore.currentBudgetId, groupId)
      envelopeGroups.value = envelopeGroups.value.filter((g) => g.id !== groupId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete group'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function transferBetweenEnvelopes(
    fromId: string,
    toId: string,
    amount: number
  ): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiTransfer(authStore.currentBudgetId, {
        from_envelope_id: fromId,
        to_envelope_id: toId,
        amount,
      })
      // Refresh envelopes to get updated balances
      await fetchEnvelopes()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to transfer'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getEnvelopeById(envelopeId: string): Envelope | undefined {
    return envelopes.value.find((e) => e.id === envelopeId)
  }

  function getGroupById(groupId: string): EnvelopeGroup | undefined {
    return envelopeGroups.value.find((g) => g.id === groupId)
  }

  async function toggleStarred(envelopeId: string): Promise<Envelope> {
    const envelope = getEnvelopeById(envelopeId)
    if (!envelope) throw new Error('Envelope not found')
    return await updateEnvelope(envelopeId, { is_starred: !envelope.is_starred })
  }

  // Date range management
  function setDateRange(preset: DateRangePreset, customStart?: string, customEnd?: string): void {
    const now = new Date()

    switch (preset) {
      case 'this_month':
        dateRange.value = {
          startDate: formatDate(getFirstDayOfMonth(now)),
          endDate: formatDate(now), // Today, not end of month
          preset: 'this_month',
        }
        break
      case 'last_month':
        dateRange.value = {
          startDate: formatDate(getFirstDayOfPreviousMonth(now)),
          endDate: formatDate(getLastDayOfPreviousMonth(now)),
          preset: 'last_month',
        }
        break
      case 'last_3_months':
        dateRange.value = {
          startDate: formatDate(getFirstDayOfNMonthsAgo(now, 3)),
          endDate: formatDate(now),
          preset: 'last_3_months',
        }
        break
      case 'year_to_date':
        dateRange.value = {
          startDate: formatDate(getFirstDayOfYear(now)),
          endDate: formatDate(now),
          preset: 'year_to_date',
        }
        break
      case 'custom':
        if (customStart && customEnd) {
          dateRange.value = {
            startDate: customStart,
            endDate: customEnd,
            preset: 'custom',
          }
        }
        break
    }
  }

  // Fetch budget summary
  async function fetchBudgetSummary(): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      budgetSummaryLoading.value = true
      error.value = null
      budgetSummary.value = await getEnvelopeBudgetSummary(
        authStore.currentBudgetId,
        dateRange.value.startDate,
        dateRange.value.endDate
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch budget summary'
      throw e
    } finally {
      budgetSummaryLoading.value = false
    }
  }

  // Fetch envelope activity
  async function fetchEnvelopeActivity(envelopeId: string): Promise<EnvelopeActivityResponse> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      return await getEnvelopeActivity(
        authStore.currentBudgetId,
        envelopeId,
        dateRange.value.startDate,
        dateRange.value.endDate
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch envelope activity'
      throw e
    }
  }

  function reset() {
    envelopes.value = []
    envelopeGroups.value = []
    unfundedCcDebt.value = 0
    budgetSummary.value = null
    error.value = null
    isEditMode.value = false
    // Reset date range to current month
    const now = new Date()
    dateRange.value = {
      startDate: formatDate(getFirstDayOfMonth(now)),
      endDate: formatDate(now),
      preset: 'this_month',
    }
  }

  // Edit mode and reordering
  function toggleEditMode() {
    isEditMode.value = !isEditMode.value
  }

  // Get sorted groups (by sort_order, then name)
  function getSortedGroups(): EnvelopeGroup[] {
    return [...envelopeGroups.value].sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.name.localeCompare(b.name)
    })
  }

  // Get sorted envelopes in a group (excluding unallocated and credit card envelopes)
  function getEnvelopesInGroup(groupId: string | null): Envelope[] {
    return envelopes.value
      .filter(
        (e) =>
          e.envelope_group_id === groupId &&
          !e.is_unallocated &&
          !e.linked_account_id &&
          e.is_active
      )
      .sort((a, b) => {
        if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
        return a.name.localeCompare(b.name)
      })
  }

  // Check if envelope is first in its group
  function isEnvelopeFirst(envelopeId: string): boolean {
    const envelope = envelopes.value.find((e) => e.id === envelopeId)
    if (!envelope) return true
    const groupEnvelopes = getEnvelopesInGroup(envelope.envelope_group_id)
    return groupEnvelopes[0]?.id === envelopeId
  }

  // Check if envelope is last in its group
  function isEnvelopeLast(envelopeId: string): boolean {
    const envelope = envelopes.value.find((e) => e.id === envelopeId)
    if (!envelope) return true
    const groupEnvelopes = getEnvelopesInGroup(envelope.envelope_group_id)
    return groupEnvelopes[groupEnvelopes.length - 1]?.id === envelopeId
  }

  // Check if group is first
  function isGroupFirst(groupId: string): boolean {
    const sortedGroups = getSortedGroups()
    return sortedGroups[0]?.id === groupId
  }

  // Check if group is last
  function isGroupLast(groupId: string): boolean {
    const sortedGroups = getSortedGroups()
    return sortedGroups[sortedGroups.length - 1]?.id === groupId
  }

  // Initialize sort orders if any items have sort_order=0
  async function initializeSortOrders(): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    // Check if initialization is needed for groups
    const groupsNeedInit = envelopeGroups.value.some((g) => g.sort_order === 0)

    // Check if initialization is needed for envelopes (excluding unallocated and CC)
    const envelopesNeedInit = envelopes.value.some(
      (e) => !e.is_unallocated && !e.linked_account_id && e.sort_order === 0
    )

    if (!groupsNeedInit && !envelopesNeedInit) return

    reorderLoading.value = true
    try {
      // Initialize groups
      if (groupsNeedInit) {
        const sortedGroups = getSortedGroups()
        for (let i = 0; i < sortedGroups.length; i++) {
          const group = sortedGroups[i]
          if (!group) continue
          const newOrder = (i + 1) * 10
          if (group.sort_order !== newOrder) {
            await updateEnvelopeGroup(group.id, { sort_order: newOrder })
          }
        }
      }

      // Initialize envelopes per group (including ungrouped)
      if (envelopesNeedInit) {
        const groupIds = [
          ...new Set(
            envelopes.value
              .filter((e) => !e.is_unallocated && !e.linked_account_id)
              .map((e) => e.envelope_group_id)
          ),
        ]

        for (const groupId of groupIds) {
          const groupEnvelopes = getEnvelopesInGroup(groupId)
          for (let i = 0; i < groupEnvelopes.length; i++) {
            const envelope = groupEnvelopes[i]
            if (!envelope) continue
            const newOrder = (i + 1) * 10
            if (envelope.sort_order !== newOrder) {
              await updateEnvelope(envelope.id, { sort_order: newOrder })
            }
          }
        }
      }

      // Refresh data
      await fetchEnvelopes()
    } finally {
      reorderLoading.value = false
    }
  }

  // Move envelope up within its group
  async function moveEnvelopeUp(envelopeId: string): Promise<void> {
    const envelope = envelopes.value.find((e) => e.id === envelopeId)
    if (!envelope || envelope.is_unallocated || envelope.linked_account_id) return

    const groupEnvelopes = getEnvelopesInGroup(envelope.envelope_group_id)
    const currentIndex = groupEnvelopes.findIndex((e) => e.id === envelopeId)
    if (currentIndex <= 0) return // Already at top

    const prevEnvelope = groupEnvelopes[currentIndex - 1]
    if (!prevEnvelope) return
    await swapEnvelopeSortOrders(envelope, prevEnvelope)
  }

  // Move envelope down within its group
  async function moveEnvelopeDown(envelopeId: string): Promise<void> {
    const envelope = envelopes.value.find((e) => e.id === envelopeId)
    if (!envelope || envelope.is_unallocated || envelope.linked_account_id) return

    const groupEnvelopes = getEnvelopesInGroup(envelope.envelope_group_id)
    const currentIndex = groupEnvelopes.findIndex((e) => e.id === envelopeId)
    if (currentIndex < 0 || currentIndex >= groupEnvelopes.length - 1) return // Already at bottom

    const nextEnvelope = groupEnvelopes[currentIndex + 1]
    if (!nextEnvelope) return
    await swapEnvelopeSortOrders(envelope, nextEnvelope)
  }

  // Swap sort orders between two envelopes
  async function swapEnvelopeSortOrders(
    envelope1: Envelope,
    envelope2: Envelope
  ): Promise<void> {
    reorderLoading.value = true
    try {
      const temp = envelope1.sort_order
      await updateEnvelope(envelope1.id, { sort_order: envelope2.sort_order })
      await updateEnvelope(envelope2.id, { sort_order: temp })
    } finally {
      reorderLoading.value = false
    }
  }

  // Move group up
  async function moveGroupUp(groupId: string): Promise<void> {
    const sortedGroups = getSortedGroups()
    const currentIndex = sortedGroups.findIndex((g) => g.id === groupId)
    if (currentIndex <= 0) return // Already at top

    const prevGroup = sortedGroups[currentIndex - 1]
    const currentGroup = sortedGroups[currentIndex]
    if (!prevGroup || !currentGroup) return
    await swapGroupSortOrders(currentGroup, prevGroup)
  }

  // Move group down
  async function moveGroupDown(groupId: string): Promise<void> {
    const sortedGroups = getSortedGroups()
    const currentIndex = sortedGroups.findIndex((g) => g.id === groupId)
    if (currentIndex < 0 || currentIndex >= sortedGroups.length - 1) return // Already at bottom

    const nextGroup = sortedGroups[currentIndex + 1]
    const currentGroup = sortedGroups[currentIndex]
    if (!nextGroup || !currentGroup) return
    await swapGroupSortOrders(currentGroup, nextGroup)
  }

  // Swap sort orders between two groups
  async function swapGroupSortOrders(
    group1: EnvelopeGroup,
    group2: EnvelopeGroup
  ): Promise<void> {
    reorderLoading.value = true
    try {
      const temp = group1.sort_order
      await updateEnvelopeGroup(group1.id, { sort_order: group2.sort_order })
      await updateEnvelopeGroup(group2.id, { sort_order: temp })
    } finally {
      reorderLoading.value = false
    }
  }

  return {
    // State
    envelopes,
    envelopeGroups,
    unfundedCcDebt,
    loading,
    error,
    isEditMode,
    reorderLoading,
    // Budget summary state
    dateRange,
    budgetSummary,
    budgetSummaryLoading,
    // Getters
    totalBudgeted,
    unallocatedBalance,
    unallocatedEnvelope,
    activeEnvelopes,
    overspentEnvelopes,
    creditCardEnvelopes,
    starredEnvelopes,
    envelopesByGroup,
    // Actions
    fetchEnvelopes,
    fetchEnvelopeGroups,
    fetchEnvelope,
    createEnvelope,
    updateEnvelope,
    deleteEnvelope,
    createEnvelopeGroup,
    updateEnvelopeGroup,
    deleteEnvelopeGroup,
    transferBetweenEnvelopes,
    getEnvelopeById,
    getGroupById,
    toggleStarred,
    reset,
    // Budget summary actions
    setDateRange,
    fetchBudgetSummary,
    fetchEnvelopeActivity,
    // Reordering
    toggleEditMode,
    initializeSortOrders,
    getSortedGroups,
    getEnvelopesInGroup,
    isEnvelopeFirst,
    isEnvelopeLast,
    isGroupFirst,
    isGroupLast,
    moveEnvelopeUp,
    moveEnvelopeDown,
    moveGroupUp,
    moveGroupDown,
  }
})
